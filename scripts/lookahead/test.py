from lookahead import Lookahead

def testLoadingAndAppendingSegments():
    la = Lookahead(5)
    la.load_segment(0)
    before = len(la.lookahead[u'mjds'])
    la.load_segment(1)
    after = len(la.lookahead[u'mjds'])
    assert before < after

def testEndOfNightArraySlicing():
    la = Lookahead(5)
    la.load_segment(0)

if __name__ == "__main__":
    testLoadingAndAppendingSegments()


