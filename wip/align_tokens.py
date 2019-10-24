from spacy.gold import align
from collections import defaultdict

def remove_bertie_stuff(tokens):
    new_tokens=[]
    for i, token in enumerate(tokens):
        if i==0 or i==len(tokens)-1: continue
        if token.startswith('##'): token=token[2:]
        new_tokens.append(token)
    return new_tokens

def align_bert_to_spacy(bert_tokens, spacy_tokens):
    other_tokens=remove_bertie_stuff(bert_tokens)
    print(other_tokens)
    cost, b2s, s2b, b2s_multi, s2b_multi = align(other_tokens, spacy_tokens)
    print("Misaligned tokens:", cost)  # 2
    print("One-to-one mappings bert -> spacy", b2s)  # array([0, 1, 2, 3, -1, -1, 5, 6])
    print("One-to-one mappings spacy -> bert", s2b)  # array([0, 1, 2, 3, 5, 6, 7])
    print("Many-to-one mappings bert -> spacy", b2s_multi)  # {4: 4, 5: 4}
    print("Many-to-one mappings spacy -> bert", s2b_multi)  # {}

    bert2spacy=defaultdict(list)
    spacy2bert=defaultdict(list)
    for bert_index, spacy_index  in enumerate(b2s):
        if spacy_index!=-1:
            bert2spacy[bert_index].append(spacy_index)
            spacy2bert[spacy_index].append(bert_index)
        else:
            bert2spacy[bert_index].append(b2s_multi[bert_index])
            spacy2bert[b2s_multi[bert_index]].append(bert_index)
    print(bert2spacy)       
    print(spacy2bert)
    return bert2spacy, spacy2bert

bert_tokens=['[CLS]', 'after', '5', 'months', 'and', '48', 'games', ',', 'the', 'match', 'was', 'abandoned', 'in', 'controversial', 'circumstances', 'with', 'ka', '##rp', '##ov', 'leading', 'five', 'wins', 'to', 'three', '(', 'with', '40', 'draws', ')', ',', 'and', 'replay', '##ed', 'in', 'the', 'world', 'chess', 'championship', '1985', '.', '[SEP]']
spacy_tokens=['after', '5', 'months', 'and', '48', 'games', ',', 'the', 'match', 'was', 'abandoned', 'in', 'controversial', 'circumstances', 'with', 'karpov', 'leading', 'five', 'wins', 'to', 'three', '(', 'with', '40', 'draws', ')', ',', 'and', 'replayed', 'in', 'the', 'world', 'chess', 'championship', '1985', '.']
results=align_bert_to_spacy(bert_tokens, spacy_tokens)