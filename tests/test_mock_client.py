from tests.mock_llm import MockClient


def test_mock_client_postprocess():
    client = MockClient(prefix="> ")
    messages = [{"role": "user", "content": "hello world"}]
    reply = client.query(messages, max_chars=5)
    assert reply == "> hello"
    assert client.queries == [(messages, 5)]
