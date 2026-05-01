from autoedit.align import normalize, tokenize_script


def test_normalize_strips_punct_and_lowercases():
    assert normalize("안녕하세요!") == "안녕하세요"
    assert normalize("Bitcoin.") == "bitcoin"
    assert normalize("  다시  ") == "다시"


def test_tokenize_script_assigns_sentence_indices():
    script = "안녕하세요. 오늘은 비트코인 시황입니다.\n5만 달러를 돌파했습니다!"
    tokens = tokenize_script(script)
    texts = [t.text for t in tokens]
    assert "안녕하세요" in texts
    assert "비트코인" in texts
    sentences = {t.sentence_idx for t in tokens}
    assert len(sentences) >= 2
