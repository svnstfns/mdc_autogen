import tiktoken


def get_tokenizer(model):
    return tiktoken.encoding_for_model(model)


def tokenize(text, tokenizer):
    return tokenizer.encode(text)
