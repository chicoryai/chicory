import litserve as ls

from pprint import pprint
from datetime import datetime, UTC

from services.workflows.data_understanding.hybrid_rag.adaptive_rag_v2 import initialize_brewsearch_state_workflow


class DiscoverChatAPI(ls.LitAPI):
    def setup(self, devices):
        # Compile
        self.query_engine = initialize_brewsearch_state_workflow()

    def decode_request(self, request):
        return request["query"]

    def predict(self, query):
        return self.run(query, self.query_engine)

    def encode_response(self, output):
        return {"output": output}

    async def run(self, question: str, app):
        # Run
        inputs = {
            "question": question
        }
        config = {
            "recursion_limit": 50,
            "configurable": {
                "thread_id": "chicory-ui-discovery",  # Generate a unique thread ID
                "thread_ts": datetime.now(UTC).isoformat()  # Use the current UTC timestamp
            }
        }
        try:
            async for event in app.astream(inputs, config=config):
                for key, value in event.items():
                    pprint(f"Node '{key}':")
                    # if key != "__end__":
                    #     print(value)

            # Final generation
            pprint(value["generation"])
            return value["generation"]
        except Exception as e:
            print(e)
            return f"Try again. {str(e)}"

if __name__ == "__main__":
    api = DiscoverChatAPI()
    server = ls.LitServer(api)
    server.run(port=8000)