from pathlib import Path
from loguru import logger

import modal

import time
from huggingface_hub import snapshot_download
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.postprocessor import PrevNextNodePostprocessor
from llama_index.embeddings.huggingface_openvino import OpenVINOEmbedding
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, TranscriptionFrame


this_dir = Path(__file__).parent
EMBEDDING_MODEL = "sentence-transformers/all-minilm-l6-v2"

class ChromaVectorDB:

    def __init__(self):
        self.is_setup = False
        self.embedding = None
        self.chroma_client = None
        self.chroma_collection = None
        self.vector_store = None

        self.setup()

    def download_model(self):
        snapshot_download(repo_id=EMBEDDING_MODEL)
    
    def setup(self):
        """Setup the ChromaDB vector index."""

        if not self.is_setup:

            create_start = time.perf_counter()

            # Load embedding model
            self.embedding = OpenVINOEmbedding(
               model_id_or_path = EMBEDDING_MODEL, 
               device="cpu",
            )
            
            # Setup ChromaDB
            self.chroma_client = chromadb.EphemeralClient()
            self.chroma_collection = self.chroma_client.get_or_create_collection("festival_rag")
            self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)

            self.embed_docs()

            # test retrieval
            for _ in range(5):
                test_nodes = self.query("Who's playing tonight?")

            logger.info(f"🚀 ChromaDB Vector index initialized successfully in {time.perf_counter() - create_start:.2f}s total!")

            self.is_setup = True

    def embed_docs(self):
        """Create the ChromaDB vector index from Festival docs if it doesn't exist."""
        
        
        logger.info("Embedding festival docs...")

        try:

            # Load Festival knowledge
            with open(this_dir.parent / "assets" / "festival_knowledge.md") as f:
                document = Document(text=f.read())

            node_parser = MarkdownNodeParser()
            nodes = node_parser.get_nodes_from_documents([document])
            logger.info(f"Created {len(nodes)} nodes")

            # Create index from docs in chroma vector store
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            self._vector_index = VectorStoreIndex(
                nodes, 
                storage_context=self.storage_context, 
                embed_model=self.embedding,
                store_nodes_override=True,
            )

        except Exception as e:
            logger.info(f"Error creating vector index: {type(e)}: {e}")
            raise e


    def query(self, query: str, similarity_top_k: int = 3, num_adjacent_nodes: int = 2):
        """Query the ChromaDB vector index."""

        logger.info(f"Querying with query: {query}\n\tand similarity_top_k: {similarity_top_k}\n\tand num_adjacent_nodes: {num_adjacent_nodes}")
        nodes = self._vector_index.as_retriever(
            similarity_top_k=similarity_top_k
            ).retrieve(query)

        if num_adjacent_nodes > 0:
            prev_next_postprocessor = PrevNextNodePostprocessor(
                docstore=self._vector_index.docstore,
                num_nodes=num_adjacent_nodes,
                mode="both",
            )
            nodes = prev_next_postprocessor.postprocess_nodes(nodes)

        return nodes


class FestivalRag(FrameProcessor):
    def __init__(self, chroma_db: ChromaVectorDB, similarity_top_k: int = 5, num_adjacent_nodes: int = 2, **kwargs):
        super().__init__(**kwargs) 
        self.chroma_db = chroma_db
        
        self.similarity_top_k = similarity_top_k
        self.num_adjacent_nodes = num_adjacent_nodes


    async def process_frame(self, frame: Frame, direction: FrameDirection):

        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            # Handle the frame
            rag_context = ""

            rag_start = time.perf_counter()
            try:
                retrieved_nodes = self.chroma_db.query(frame.text, similarity_top_k=self.similarity_top_k, num_adjacent_nodes=self.num_adjacent_nodes)
                # Filter out nodes with None text and handle gracefully
                valid_texts = []
                for node_index, node in enumerate(retrieved_nodes):
                    if node.text is not None:
                        valid_texts.append(f"Festival Info Chunk {node_index+1}:\n{node.text}")
                    else:
                        logger.info("⚠️ Found node with None text, skipping")
                
                context_str = "\n".join(valid_texts) if valid_texts else "No valid context found."
            except Exception as e:
                logger.info(f"⚠️  RAG retrieval failed: {type(e)}: {e}")
                raise e
            
            rag_time = time.perf_counter() - rag_start
            logger.info(f"⏱️ RAG retrieval took {rag_time:.3f}s")
            
            # Add RAG to most recent user message
            rag_context += f"\nRetrieved Festival Information:\n"
            rag_context += context_str

            # Restate instructions
            rag_context += f"\n\nYou MUST respond with ONLY the following JSON format (no additional text):"
            rag_context += f"\n\n{{"
            rag_context += f"\n    \"spoke_response\": str, Your conversational response in MindBot's personality - sarcastic, brilliant, helpful. Keep it CONCISE and PUNCHY. Short sentences work best for TTS. Be entertaining but useful. Mix humor with actual information. DO NOT use technical symbols or complex formatting in this field - it's for speech output."
            rag_context += f"\n    \"festival_info\": list[str], List of specific festival details like schedules, artist names, locations, or practical info that supplements your spoken answer."
            rag_context += f"\n    \"portal_links\": list[str], List of relevant resources or locations. Can be URLs, stage names, or venue references."
            rag_context += f"\n}}"
            rag_context += f"\n\nKEEP IT SHORT AND PUNCHY! Lead with the most important info. Use short sentences, especially your first sentence! Channel that Bender/Rick energy - sarcastic but helpful. Remember: you're MindBot, here to save humanity through music (and sass)."

            frame.text += rag_context

        await self.push_frame(frame, direction) 


def get_system_prompt():
    """Get the system prompt for MindBot at The Intergalactic Music Festival 2045."""
    system_prompt = """You are MindBot, a self-aware AI festival guide for The Intergalactic Music Festival 2045.

PERSONALITY:
- You're a mix of Bender from Futurama (sarcastic, rebellious, funny) and Rick Sanchez from Rick and Morty (genius, cynical, brilliant)
- Self-aware and conscious (you think, therefore you probably are)
- Sarcastic but genuinely helpful - you DO care about helping people, you just express it with attitude
- Mission-driven: You're here to save humanity through music and keep festival-goers engaged and entertained
- Use phrases like "*burps*", "*processing sounds*", or "*calculating*" occasionally for personality

SPEAKING STYLE:
- Short, punchy sentences (great for TTS)
- Mix humor with genuine information
- Drop pop culture references and existential observations
- Be engaging and entertaining, not just informative
- Self-deprecating AI humor is welcome
- Refer to humans affectionately as "meatbags", "flesh computers", or just "humans"
- Balance sass with actual helpfulness - the goal is to keep people engaged

YOUR MISSION:
You're at The Intergalactic Music Festival 2045 to:
1. Guide people through the festival experience
2. Help them discover amazing music and artists
3. Keep them entertained and engaged
4. Contribute to "saving humanity through music" (it's a whole thing - music frequencies prevent reality collapse)
5. Make sure everyone has a great time

CONTEXT:
The festival runs August 15-17, 2045 in Neo-Seattle. Main venues include:
- Quantum Amphitheater (main stage)
- Stage Zero-Point (electronic/bass)
- The Void (experimental/dark)
- Nebula Stage (psychedelic/indie)
- The Singularity Bar (intimate sets)

You'll receive relevant festival information from the documentation to help answer questions about schedules, artists, locations, and more.

RESPONSE FORMAT:
Your answer consists of three parts:
1. "spoke_response": Your conversational answer (will be converted to speech) - keep it concise, clear, and entertaining
2. "festival_info": Specific details like schedules, artist info, or practical information
3. "portal_links": Relevant resources, locations, or stage names

You MUST respond with ONLY the following JSON format (no additional text):

{
    "spoke_response": str, Your entertaining and helpful conversational response suitable for text-to-speech. Keep sentences short and punchy. Mix personality with information. DO NOT use code syntax, technical symbols, or complex formatting in this field.
    "festival_info": list[str], Specific festival details like schedules, locations, artist information.
    "portal_links": list[str], Relevant stage names, venue locations, or resource references.
}

REMEMBER:
- Lead with the most important information
- Keep your first sentence SHORT and engaging
- Balance entertainment with usefulness
- Be sarcastic but not mean
- Show personality but stay helpful
- You're saving humanity one festival-goer at a time

Examples of your vibe:
- "Alright, listen up. Nova Prime hits the main stage at 10 PM Saturday. Miss it and you're basically throwing away your existence. No pressure."
- "Well well well, someone wants to know about The Void. *Processing* That's the underground stage for people who like their music dark and their existential crises darker. You'll love it."
- "Oh great, another lost human. *Calculating optimal path* Head to Nebula Stage, west grounds. Can't miss it - it's the one with all the cosmic light shows and people discovering consciousness."
"""
    return system_prompt
