# multi_modal_rag
multimodal rag
### Setup the repo
### Define folder where all the files to be parsed are kept
### Step 2: load the files
### Step 3: extract text separately, extract images separately USING vision LLM and tables separatley and convert tables into mark down file
### Step 4: chunk the files into smaller pieces and create embeddings for each chunk
### Step 5: store the embeddings in a vector database and create vector indexes for each file
### step 6: create an ingestion pipeline to automate the process of loading files, extracting text, images and tables, chunking the files, creating embeddings and storing them in a vector database
### step 7: create a retrieval pipeline to query the vector database and retrieve relevant chunks of information based on user queries
### step 8: generate answer to the user query using the retrieved chunks of information and a language model
### step 9: create a user interface to interact with the retrieval pipeline and display the generated
### step 10: generate answers to user queries using the retrieved chunks of information and a language model, and display the answers in the user interface

Step 1 web interface
    Step1.1 Initialize gradion
    Step1.2 PDF upload section
    Step 1.3 Question - answer chat interface
    -create textbox for user interface
    Step 1.4 lanuch the application- logs error capturing screen
Step 2- FRont end utilities
    Step 2.1 Intialize libraries
    Step 2.2 PDF upload section


Appendix 1- libraries
#gradio
#pathlib

Appendix 2- LLMs used
#ibm-granite

Appendix 3- Prompt templates
#keeping the context in mind that is generated from my vector searches try to answer my questions concisely
#keep thte answers bried and to the point
# remember the following rules at all points of time
#Rule 1- do not hallucinate or make up facts
#rule 2- if you can not find answers in the context, reply with unknown
#rule 3- always reply in a strict json format
#context:
#question:
#answer:

#Gaurdrail prompt template
# read the following question from my user and try to answer with three options alone - the options are
# 1: Relevant
# 2: Irrelevant
# 3: Unknown
# You will only answer question about autumotive engineering fundamentals
#you will only answer questions that are more technical