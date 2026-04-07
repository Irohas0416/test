import os
import pandas as pd

from schema.schema import ExtractionData, Person

from langchain_community.document_loaders import TextLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# 1. Set your Gemini API Key
# Best practice: Set this in your terminal environment variables: export GOOGLE_API_KEY="your_key"
os.environ["GOOGLE_API_KEY"] = "AIzaSyCAThbtQng5E7RAtigtITQ3Q3GVEsGr9xQ" 


def main():
    # 3. Load the Input File
    # Create a dummy file named 'input.txt' in your directory to test this.
    try:
        loader = TextLoader("input.txt")
        docs = loader.load()
        file_content = docs[0].page_content
    except FileNotFoundError:
        print("Error: 'input.txt' not found. Please create one to test.")
        return

    # 4. Initialize the Gemini Model
    # gemini-1.5-flash is extremely fast and cost-effective for extraction tasks.
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0)
    
    # Bind our Pydantic schema to the model
    structured_llm = llm.with_structured_output(ExtractionData)

    # 5. Create the Prompt Template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert data extraction algorithm. Extract all people mentioned in the provided text. Only extract information explicitly mentioned."),
        ("human", "{text}")
    ])

    # 6. Build and Invoke the Chain
    print("Processing file with Gemini...")
    chain = prompt | structured_llm
    result = chain.invoke({"text": file_content})

    # 7. Convert Output to CSV
    if result.people:
        # Convert Pydantic objects to dictionaries
        data_dicts = [person.model_dump() for person in result.people]
        
        # Load into Pandas DataFrame and save to CSV
        df = pd.DataFrame(data_dicts)
        df.to_csv("extracted_people.csv", index=False)
        print("\nSuccess! Extracted data saved to 'extracted_people.csv'.")
        print(df.head())
    else:
        print("No people were found in the text.")

if __name__ == "__main__":
    main()