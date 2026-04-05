# ============================================================
# Multimodal RAG Web Interface - Gradio Application
# ============================================================
# Step 1: Web Interface
#   Step1.1: Initialize Gradio
#   Step1.2: PDF upload section
#   Step 1.3: Question-answer chat interface with textbox
#   Step 1.4: Launch the application with error handling & logging
#
# Step 2: Frontend utilities
#   Step 2.1: Initialize libraries
#   Step 2.2: PDF upload section
#
# Appendix 1: Libraries used - gradio, pathlib
# Appendix 2: LLMs used - ibm-granite
# Appendix 3: Prompt templates with strict response rules
# ============================================================

# ============================================================
# STEP 2.1: Initialize Libraries
# ============================================================
import gradio as gr
import json
import logging
import traceback
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime
import shutil
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# Prompt Templates - Appendix 3
# ============================================================
class PromptTemplates:
    """Prompt templates for the RAG system."""
    
    @staticmethod
    def get_answer_prompt(context: str, question: str) -> str:
        """
        Get the main answer prompt template.
        Rules:
        - Rule 1: Do not hallucinate or make up facts
        - Rule 2: If you cannot find answers in the context, reply with 'unknown'
        - Rule 3: Always reply in strict JSON format
        """
        prompt = f"""Based on the following context, answer the user's question concisely and to the point.

Remember the following rules:
1. Do not hallucinate or make up facts
2. If you cannot find the answer in the context, reply with 'unknown'
3. Always reply in strict JSON format with this structure:
   {{"context": "relevant_context_snippet", "question": "{question}", "answer": "your_answer"}}

Context:
{context}

Question: {question}

Answer in JSON format only:"""
        return prompt
    
    @staticmethod
    def get_guardrail_prompt(question: str) -> str:
        """
        Get the guardrail prompt template.
        Categorizes questions as:
        1: Relevant (automotive engineering fundamentals)
        2: Irrelevant (off-topic)
        3: Unknown (unclear)
        """
        prompt = f"""Read the following question and categorize it into ONE of these options:
1: Relevant (question is about automotive engineering fundamentals or technical topics)
2: Irrelevant (question is off-topic)
3: Unknown (unclear or cannot determine)

You will only answer questions about automotive engineering fundamentals.
You will only answer questions that are technical in nature.

Question: {question}

Respond with ONLY the number (1, 2, or 3) and a brief reason in JSON format:
{{"category": number, "reason": "brief_explanation"}}"""
        return prompt


# ============================================================
# STEP 1.1 & 1.2: RAG Interface Class
# ============================================================
class RAGInterface:
    """Interface for the Multimodal RAG system."""
    
    def __init__(self, sample_docs_path: str = "sample documents"):
        """Initialize the RAG interface."""
        self.sample_docs_path = Path(sample_docs_path)
        self.uploaded_files = []
        self.chat_history = []
        logger.info("RAG Interface initialized")
    
    # STEP 2.2: PDF Upload Section
    def handle_file_upload(self, files: List) -> str:
        """
        Handle PDF/document upload.
        
        Args:
            files: List of uploaded files
            
        Returns:
            str: Status message
        """
        try:
            if not files:
                return "❌ No files uploaded"
            
            self.uploaded_files = []
            for file in files:
                file_path = Path(file.name)
                self.uploaded_files.append(str(file_path))
                logger.info(f"File uploaded: {file.name}")
            
            status = f"✅ Successfully uploaded {len(files)} file(s):\n"
            for file_info in self.uploaded_files:
                status += f"  • {Path(file_info).name}\n"
            
            logger.info(f"Total files uploaded: {len(self.uploaded_files)}")
            return status
        
        except Exception as e:
            error_msg = f"❌ Error uploading files: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return error_msg
    
    # STEP 1.3: Question-Answer Chat Interface
    def process_question(self, question: str, chat_history: List[Tuple]) -> Tuple[str, List[Tuple]]:
        """
        Process user question and generate response.
        
        Args:
            question: User's question
            chat_history: Previous chat messages
            
        Returns:
            Tuple containing response and updated chat history
        """
        try:
            if not question.strip():
                return "⚠️ Please enter a question", chat_history
            
            if not self.uploaded_files:
                response = json.dumps({
                    "context": "No documents uploaded",
                    "question": question,
                    "answer": "unknown"
                }, indent=2)
                logger.warning("Question asked without uploaded documents")
            else:
                # Create simulated context from uploaded files
                context = f"Documents loaded: {', '.join([Path(f).name for f in self.uploaded_files])}\n"
                context += "Processing query against vector database..."
                
                # Get guardrail check
                guardrail_check = self._check_guardrail(question)
                
                if guardrail_check.get("category") != 1:
                    response = json.dumps({
                        "context": "Question relevance check",
                        "question": question,
                        "answer": f"unknown - Question is {guardrail_check.get('reason', 'not relevant')}"
                    }, indent=2)
                else:
                    # Create response following the prompt template
                    response = json.dumps({
                        "context": context,
                        "question": question,
                        "answer": "This is a response based on the uploaded documents. (RAG processing would occur here with actual model inference)"
                    }, indent=2)
                
                logger.info(f"Question processed: {question[:50]}...")
            
            # Update chat history
            chat_history.append((question, response))
            return response, chat_history
        
        except Exception as e:
            error_response = json.dumps({
                "context": "Error processing question",
                "question": question,
                "answer": "error",
                "error_details": str(e)
            }, indent=2)
            logger.error(f"Error processing question: {traceback.format_exc()}")
            return error_response, chat_history
    
    def _check_guardrail(self, question: str) -> Dict[str, Any]:
        """Check if question meets guardrail criteria."""
        # Basic guardrail check - can be enhanced with actual LLM
        automotive_keywords = ['automotive', 'vehicle', 'engine', 'transmission', 'chassis', 'suspension', 
                              'brake', 'steering', 'electrical', 'hybrid', 'evp', 'car', 'truck', 'motor']
        
        question_lower = question.lower()
        is_technical = any(keyword in question_lower for keyword in automotive_keywords)
        
        if is_technical:
            return {"category": 1, "reason": "Relevant technical automotive question"}
        elif any(word in question_lower for word in ['what', 'how', 'why', 'describe', 'explain']):
            return {"category": 1, "reason": "Technical question"}
        else:
            return {"category": 3, "reason": "Unclear or unclear relevance"}
    
    def clear_chat(self) -> Tuple[str, List]:
        """Clear chat history."""
        self.chat_history = []
        logger.info("Chat history cleared")
        return "", []
    
    def clear_uploads(self) -> str:
        """Clear uploaded files."""
        self.uploaded_files = []
        logger.info("Uploaded files cleared")
        return "✅ Uploads cleared"


# ============================================================
# STEP 1.1: Initialize Gradio Interface
# ============================================================
def create_gradio_interface() -> gr.Blocks:
    """
    Create and configure the Gradio web interface.
    
    Returns:
        gr.Blocks: Configured Gradio interface
    """
    rag_interface = RAGInterface()
    
    with gr.Blocks(title="Multimodal RAG Assistant", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🤖 Multimodal RAG Assistant
        ### Automotive Engineering Knowledge Base
        
        Upload PDF documents and ask questions about automotive engineering fundamentals.
        
        **Instructions:**
        1. Upload your PDF documents using the file uploader
        2. Ask questions in the chat interface
        3. Receive answers based on the uploaded documents
        """)
        
        with gr.Row():
            # Left column - Document Upload Section
            with gr.Column(scale=1):
                gr.Markdown("### 📄 Document Upload")
                file_upload = gr.File(
                    label="Upload PDF/Documents",
                    file_count="multiple",
                    file_types=[".pdf", ".docx", ".txt", ".md"]
                )
                upload_button = gr.Button("📤 Upload Documents", variant="primary")
                upload_status = gr.Textbox(
                    label="Upload Status",
                    interactive=False,
                    lines=4
                )
                clear_upload_btn = gr.Button("🗑️ Clear Uploads", variant="stop")
            
            # Right column - Chat Interface
            with gr.Column(scale=2):
                gr.Markdown("### 💬 Q&A Chat Interface")
                
                # Chatbot display
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=400,
                    show_copy_button=True
                )
                
                # Question input
                with gr.Row():
                    question_input = gr.Textbox(
                        placeholder="Ask a question about automotive engineering...",
                        label="Your Question",
                        lines=2,
                        scale=4
                    )
                    submit_btn = gr.Button("🚀 Ask", variant="primary", scale=1)
                
                # Chat control buttons
                with gr.Row():
                    clear_chat_btn = gr.Button("🔄 Clear Chat", variant="secondary")
                
                # System info
                gr.Markdown("""
                **Notes:**
                - Questions must be about automotive engineering fundamentals
                - Technical questions are preferred
                - Answers are based on uploaded documents only
                - All responses are in JSON format for clarity
                """)
        
        # ============================================================
        # Event Handlers
        # ============================================================
        
        # Handle file upload
        def upload_files(files):
            return rag_interface.handle_file_upload(files)
        
        upload_button.click(
            fn=upload_files,
            inputs=[file_upload],
            outputs=[upload_status]
        )
        
        # Handle question submission
        def answer_question(question, history):
            response, updated_history = rag_interface.process_question(question, history)
            return updated_history, ""  # Clear input after submit
        
        submit_btn.click(
            fn=answer_question,
            inputs=[question_input, chatbot],
            outputs=[chatbot, question_input]
        )
        
        # Allow Enter key to submit
        question_input.submit(
            fn=answer_question,
            inputs=[question_input, chatbot],
            outputs=[chatbot, question_input]
        )
        
        # Handle clear chat
        clear_chat_btn.click(
            fn=lambda: ([], ""),
            outputs=[chatbot, question_input]
        )
        
        # Handle clear uploads
        clear_upload_btn.click(
            fn=rag_interface.clear_uploads,
            outputs=[upload_status]
        )
        
        return demo


# ============================================================
# STEP 1.4: Launch the Application with Error Handling
# ============================================================
def main():
    """
    Main entry point - Launch the Gradio application.
    Includes error handling and logging.
    """
    try:
        logger.info("=" * 60)
        logger.info("Starting Multimodal RAG Web Interface")
        logger.info("=" * 60)
        
        # Create Gradio interface
        demo = create_gradio_interface()
        
        # Launch the application
        logger.info("Launching Gradio interface...")
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True
        )
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
    except Exception as e:
        error_msg = f"Fatal error during application runtime:\n{traceback.format_exc()}"
        logger.error(error_msg)
        print(f"\n❌ {error_msg}")
        raise
    finally:
        logger.info("Multimodal RAG application shut down")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()