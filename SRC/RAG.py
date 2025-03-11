# MIT License
# Copyright (c) 2025 Benedikt Horn, Sascha Tauchmann
# See the LICENSE file for more details.

from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnablePassthrough, Runnable, RunnableLambda
from langchain.schema import Document
from streamlit.runtime.scriptrunner import get_script_run_ctx
from sys import platform
if platform == "linux":
    from ragatouille import RAGPretrainedModel
else:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
import random
import shutil
import json
from typing import List, Callable, Dict
from abc import abstractmethod, ABC
from database_management import db_manager as db, template_processing as tp
from database_management.db_manager import Metrics as M

class GetCustomRetriever(ABC):
    @abstractmethod
    def __call__(self, 
        texts:List[str], n_retrieved_docs:int, index_name:str, load_from_index:bool
    ) -> BaseRetriever:
        ...
        # define retriever here
    
class GetRagaTouilleRetriever(GetCustomRetriever):
    """Used when running on a linux system"""
    def __call__(self, texts:List[str], n_retrieved_docs:int, index_name:str, load_from_index:bool):
        self.index_path = db.ragatouille_index_path(index_name)
        if load_from_index:
            RAG = RAGPretrainedModel.from_index(self.index_path)
        else:
            if self.index_path.exists() and self.index_path.is_dir():
                shutil.rmtree(self.index_path)
            RAG = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")
            RAG.index(
                collection=texts,
                index_name=index_name,
                max_document_length=1,
                split_documents=False,
            )
        return RAG.as_langchain_retriever(k=n_retrieved_docs)
    
class GetChromaRetriever(GetCustomRetriever):
    """Used when running on a non-linux system for the lack of support for RAGaTouille"""
    def __call__(self, texts:List[str], n_retrieved_docs:int, index_name:str, load_from_index:bool):
        embedding=HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-mpnet-base-v2"
        )
        index_path = str(db.chroma_index_path(index_name))
        if load_from_index:
            vectorstore = Chroma(
                collection_name=index_name,
                embedding_function=embedding,
                persist_directory=index_path
            )
        else:
            max_batch_size = 166
            if len(texts) > max_batch_size:
                texts = random.sample(texts, max_batch_size)
            vectorstore = Chroma.from_texts(
                collection_name=index_name,
                texts=texts,
                embedding=embedding,
                persist_directory=index_path
            )
        return vectorstore.as_retriever(
            search_type="mmr", 
            search_kwargs={"k": n_retrieved_docs}
        )

class RAG:
    """
    Retrieval Augmented Generation (RAG) class for retrieving similar requirement evaluations based on an input requirement.

    Attributes
    ==========

        evaluations (list): List of evaluation dictionaries loaded from the dataset.
        rating_scale (int): the scale [1, rating_scale] used for requirement evaluation.
        last_input (str): The last input requirement used to reduce computation in evaluation chains.
        last_retrieved_docs (List[Document]): The set of retrieved documents from the last input requirement.
        retriever (RunnableLambda[str, List[Document]]): A lambda function for retrieving documents based on input.

    Key Method
    ==========

        **get_inputs**
            dynamically creates a dictionary to be integrated as input of a Runnable Sequence.
            Based on the provided context template and metrics, 
            the retrieved evaluations are formatted according to `tp.process_one_shot_section`.
    """
    def __init__(self, dataset_name:str, load_retriever:bool=False, n_retrieved_docs:int=2):
        """
        Initializes the RAG class with the specified dataset and retriever settings.

        Args:
            dataset_name (str): 
                The name of the dataset (w/o '.json') to load the requirement evaluations from.
                The dataset must be stored as JSON in the `data_base/RAG_data` directory and must adher to the following format:
                
                {
                    "rating_scale": int,
                    "evaluations": [
                        RAGEvaluation(...).format_dummy,
                        ...
                    ]
                }
                
                See the `RAGEvaluation` class of the `evaluation_wrapper` module for the exact format.
                         
            load_retriever (bool, optional): Flag to indicate whether to load an existing retriever. Defaults to False.
            n_retrieved_docs (int, optional): Number of documents to retrieve. Defaults to 2.
        
        """
        eval_dict = db.load_dict_from_json_file(dataset_name, db.RAG_data)
        self.evaluations, self.rating_scale = [eval_dict[key] for key in ["evaluations", "rating_scale"]]
        reqs = [json.dumps({"req": eval["requirement"], "ID":id}) for id, eval in enumerate(self.evaluations)]
        self.last_input:str = None
        self.last_retrieved_docs:List[Document] = None
        if platform == "linux":
            get_retriever = GetRagaTouilleRetriever()
        else:
            get_retriever = GetChromaRetriever()
            if get_script_run_ctx():
                #prevent error from using ChromaDB and streamlit
                import chromadb
                chromadb.api.client.SharedSystemClient.clear_system_cache()
        inner_retriever = get_retriever(reqs, n_retrieved_docs, f"{dataset_name[:60]}_index", load_retriever)
        def retrieve_docs(input:str):
            if not (input == self.last_input and self.last_retrieved_docs):
                self.last_retrieved_docs = inner_retriever.invoke(input)
            self.last_input = input
            return self.last_retrieved_docs
        self.retriever = RunnableLambda(retrieve_docs)
    
    def _get_evaluation_extractor(self, metrics:M._list): 
        get_eval:Callable[[Document], dict] = lambda doc: self.evaluations[json.loads(doc.page_content)["ID"]]["evaluation"]
        if len(metrics) > 1:
            return get_eval
        return lambda doc: get_eval(doc)[metrics[0]]
    
    def _create_context(self, context_template:str, metrics:M._list):
        get_evaluation = self._get_evaluation_extractor(metrics)
        def save_docs(docs):
            self.last_retrieved_docs = docs
            return docs
        return lambda docs: tp.process_one_shot_section(
            tp.remove_comments(context_template), 
            evaluations=[get_evaluation(doc) for doc in save_docs(docs)], 
            rating_scale=self.rating_scale
        )

    def get_inputs(self, context_template:str, metrics:M._list=M.all) -> Dict[str, Runnable]:
        """
        Generates a dictionary of inputs for the retrieval process.

        Args:
            context_template (str): The template string for creating the context.
            metrics (M._list, optional): A list of metrics to be used in the context creation. Defaults to M.all.

        Returns:
            Dict[str, Runnable]: A dictionary containing the context and query runnables.
        """
        return {
            "context": self.retriever | self._create_context(context_template, metrics),
            "query": RunnablePassthrough()
        }
