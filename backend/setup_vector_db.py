import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_chroma import Chroma

print("Loading policy.txt...")
loader=TextLoader("../data/policy.txt")
documents=loader.load()

print("Splitting text...")
text_splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50)
chunks=text_splitter.split_documents(documents)

print("Creating Vector DB...")
embeddings=FastEmbedEmbeddings()

vector_db=Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="../data/vector_store"
)

print(f"Success! Vector DB created with {len(chunks)} chunks in '../data/vector_store'")