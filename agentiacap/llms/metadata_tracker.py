from langchain.callbacks.base import BaseCallbackHandler

class AzureTokenTracker(BaseCallbackHandler):
    def __init__(self):
        self.total_tokens = 0
        self.calls = []

    def on_llm_end(self, response, **kwargs):
        if response.llm_output and "token_usage" in response.llm_output:
            tokens_used = response.llm_output["token_usage"]["total_tokens"]
            self.total_tokens += tokens_used
            self.calls.append(tokens_used)

    def get_last_n_calls(self, n=5):
        return self.calls[-n:]

    def get_total_tokens(self):
        return self.total_tokens
