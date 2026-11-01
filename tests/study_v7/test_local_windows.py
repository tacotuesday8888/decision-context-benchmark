"""Long-document regression with a real tokenizer and a weight-free model stub."""
from contextlib import nullcontext
from types import SimpleNamespace
import unittest
from tokenizers import Tokenizer, models, pre_tokenizers
from scripts.study_v7.routes import _LocalRuntime


class Tensor:
    ndim=2
    def __init__(self,values):
        self.values=values
        self.shape=(1,len(values))


class FastTokenizer:
    def __init__(self):
        self.native=Tokenizer(models.WordLevel({'[UNK]':0,'word':1,'terminal':2},unk_token='[UNK]'))
        self.native.pre_tokenizer=pre_tokenizers.Whitespace()
        self.native.enable_truncation(max_length=512)
        self.native.enable_padding(length=512)

    def encode(self,text,*,add_special_tokens,truncation=None,padding=None):
        # Reproduce the saved backend's dangerous default unless the runtime
        # explicitly asks its fast tokenizer for the complete document.
        if truncation is False:
            self.native.no_truncation()
        if padding is False:
            self.native.no_padding()
        return self.native.encode(text,add_special_tokens=add_special_tokens).ids

    def prepare_for_model(self,chunk,**kwargs):
        return {'input_ids':Tensor([101]+chunk+[102])}


class Model:
    def __init__(self):
        self.windows=[]

    def __call__(self,*,input_ids):
        self.windows.append(input_ids.values)
        score=.95 if 2 in input_ids.values else .1
        class Logits:
            def softmax(self,axis):
                return self
            def __getitem__(self,index):
                return score
        return SimpleNamespace(logits=Logits())


class LocalWindowsTests(unittest.TestCase):
    def test_saved_512_clip_cannot_hide_terminal_window_or_maximum(self):
        runtime=object.__new__(_LocalRuntime)
        runtime.tokenizer=FastTokenizer()
        runtime.model=Model()
        runtime.torch=SimpleNamespace(inference_mode=nullcontext)
        result=runtime.classify(' '.join(['word']*1500+['terminal']))
        self.assertEqual(result['input_tokens'],1501)
        self.assertEqual(result['windows'],4)
        self.assertEqual([len(w) for w in runtime.model.windows],[512,512,512,165])
        self.assertTrue(all(2 not in w for w in runtime.model.windows[:-1]))
        self.assertIn(2,runtime.model.windows[-1])
        self.assertEqual(result['window_scores'],[.1,.1,.1,.95])
        self.assertEqual(result['score'],.95)


if __name__=='__main__':
    unittest.main()
