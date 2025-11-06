# agent.py

from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json

from .code_tools import CodeTools
from .context_builder import build_context_for_query
from config import CONFIG, SOURCE_DIRECTORY, OPENAI_API_KEY

# Define the state that flows through the graph
class AgentState:
    def __init__(self):
        self.query: str = ""
        self.intent: str = ""  # "rag", "direct", "code_tools"
        self.context: str = ""
        self.tools_used: List[str] = []
        self.tool_results: Dict[str, Any] = {}
        self.answer: str = ""
        self.tokens_used: int = 0
        self.confidence: float = 0.0

class GnomeCodeAgent:
    """
    LangGraph-based agent for GNOME code assistance.
    
    Capabilities:
    - Decides whether to use RAG, direct answers, or code tools
    - Can read files, search code, and propose edits
    - Tracks file modifications for incremental vectorization
    """
    
    def __init__(self, source_dir: str = None):
        self.source_dir = Path(source_dir) if source_dir else SOURCE_DIRECTORY
        self.code_tools = CodeTools(self.source_dir)
        self.llm = ChatOpenAI(
            model=CONFIG.model_name,
            temperature=CONFIG.temperature,
            openai_api_key=OPENAI_API_KEY
        )
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("decide", self._decide_intent)
        workflow.add_node("rag_search", self._rag_search)
        workflow.add_node("direct_answer", self._direct_answer)
        workflow.add_node("use_tools", self._use_tools)
        workflow.add_node("synthesize", self._synthesize_answer)
        
        # Set entry point
        workflow.set_entry_point("decide")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "decide",
            self._route_after_decide,
            {
                "rag": "rag_search",
                "direct": "direct_answer", 
                "tools": "use_tools"
            }
        )
        
        # All paths lead to synthesis
        workflow.add_edge("rag_search", "synthesize")
        workflow.add_edge("direct_answer", "synthesize")
        workflow.add_edge("use_tools", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _decide_intent(self, state: AgentState) -> AgentState:
        """
        Analyze user query to decide the best approach.
        """
        query = state.query.lower()
        
        # Keywords that suggest code tool usage
        code_keywords = [
            "read", "show", "file", "function", "class", "method",
            "edit", "modify", "change", "replace", "add", "remove",
            "grep", "search", "find", "where is", "definition"
        ]
        
        # Keywords that suggest RAG is needed
        rag_keywords = [
            "how does", "explain", "what is", "why", "how to",
            "architecture", "design", "workflow", "process"
        ]
        
        # Simple keyword-based routing (can be enhanced with LLM)
        code_score = sum(1 for keyword in code_keywords if keyword in query)
        rag_score = sum(1 for keyword in rag_keywords if keyword in query)
        
        if code_score > rag_score and code_score > 0:
            state.intent = "tools"
            state.confidence = 0.8
        elif rag_score > 0:
            state.intent = "rag"
            state.confidence = 0.7
        else:
            state.intent = "direct"
            state.confidence = 0.6
        
        print(f"🎯 Intent: {state.intent} (confidence: {state.confidence})")
        return state
    
    def _route_after_decide(self, state: AgentState) -> Literal["rag", "direct", "tools"]:
        """Route to appropriate node based on intent."""
        return state.intent
    
    def _rag_search(self, state: AgentState) -> AgentState:
        """
        Perform RAG search using existing pipeline.
        """
        try:
            print("🔍 Performing RAG search...")
            context_data = build_context_for_query(state.query, config=CONFIG)
            
            state.context = context_data["context_string"]
            state.tokens_used = context_data["tokens"]
            state.tools_used.append("rag_search")
            state.tool_results["rag"] = {
                "docs_found": len(context_data["docs"]),
                "tokens": context_data["tokens"]
            }
            
        except Exception as e:
            print(f"❌ RAG search failed: {e}")
            state.context = f"RAG search failed: {str(e)}"
            state.tokens_used = 0
        
        return state
    
    def _direct_answer(self, state: AgentState) -> AgentState:
        """
        Provide direct answer without RAG or tools.
        """
        print("💭 Providing direct answer...")
        
        try:
            messages = [
                SystemMessage(content="You are a helpful assistant for GNOME development. Provide clear, concise answers about programming concepts, best practices, and general development topics."),
                HumanMessage(content=state.query)
            ]
            
            response = self.llm.invoke(messages)
            state.answer = response.content
            state.tools_used.append("direct_llm")
            
        except Exception as e:
            state.answer = f"Error generating direct answer: {str(e)}"
        
        return state
    
    def _use_tools(self, state: AgentState) -> AgentState:
        """
        Use code tools to interact with the repository.
        """
        print("🛠️ Using code tools...")
        
        query = state.query
        tool_results = {}
        
        try:
            # Try to extract file path and operation from query
            if any(word in query.lower() for word in ["read", "show", "file"]):
                # Simple file reading
                if "read" in query.lower():
                    # Extract file path (simple heuristic)
                    words = query.split()
                    for i, word in enumerate(words):
                        if word.lower() == "read" and i + 1 < len(words):
                            file_path = words[i + 1]
                            result = self.code_tools.read_file(file_path)
                            tool_results["read_file"] = result
                            state.tools_used.append("read_file")
                            break
            
            # Try semantic search
            if "search" in query.lower() or "find" in query.lower():
                result = self.code_tools.search_code(query)
                tool_results["search_code"] = result
                state.tools_used.append("search_code")
            
            # Try grep search for specific patterns
            if any(word in query.lower() for word in ["grep", "pattern", "contains"]):
                # Extract pattern (simple heuristic)
                words = query.split()
                for i, word in enumerate(words):
                    if word.lower() in ["grep", "find"] and i + 1 < len(words):
                        pattern = words[i + 1]
                        result = self.code_tools.grep_search(pattern)
                        tool_results["grep_search"] = result
                        state.tools_used.append("grep_search")
                        break
            
            state.tool_results = tool_results
            
        except Exception as e:
            state.tool_results = {"error": f"Tool execution failed: {str(e)}"}
        
        return state
    
    def _synthesize_answer(self, state: AgentState) -> AgentState:
        """
        Synthesize final answer based on all gathered information.
        """
        print("🎨 Synthesizing final answer...")
        
        try:
            # Build context for synthesis
            synthesis_context = f"User Query: {state.query}\n\n"
            
            if state.context:
                synthesis_context += f"RAG Context:\n{state.context}\n\n"
            
            if state.tool_results:
                synthesis_context += f"Tool Results:\n{json.dumps(state.tool_results, indent=2)}\n\n"
            
            synthesis_context += "Provide a helpful, accurate answer based on the available information."
            
            messages = [
                SystemMessage(content="You are a helpful GNOME development assistant. Synthesize information from RAG context and tool results to provide a comprehensive answer. Be specific about file locations, code snippets, and actionable advice."),
                HumanMessage(content=synthesis_context)
            ]
            
            response = self.llm.invoke(messages)
            state.answer = response.content
            
        except Exception as e:
            state.answer = f"Error synthesizing answer: {str(e)}"
        
        return state
    
    def run(self, query: str) -> Dict[str, Any]:
        """
        Run the agent with a user query.
        
        Args:
            query: User's question or request
            
        Returns:
            Dict with answer and metadata
        """
        print(f"🤖 Processing query: {query}")
        
        # Initialize state
        initial_state = AgentState()
        initial_state.query = query
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        return {
            "query": query,
            "answer": final_state.answer,
            "intent": final_state.intent,
            "tools_used": final_state.tools_used,
            "tokens_used": final_state.tokens_used,
            "confidence": final_state.confidence,
            "tool_results": final_state.tool_results
        }


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python agent.py 'your question here'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    agent = GnomeCodeAgent()
    result = agent.run(query)
    
    print("\n" + "="*50)
    print("AGENT RESPONSE")
    print("="*50)
    print(f"Intent: {result['intent']}")
    print(f"Tools used: {', '.join(result['tools_used'])}")
    print(f"Tokens: {result['tokens_used']}")
    print(f"Confidence: {result['confidence']}")
    print("\nAnswer:")
    print(result['answer'])
