import networkx as nx
import pickle
import sys
import itertools
import numpy as np
from sklearn.cluster import DBSCAN
from collections import defaultdict
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
import copy
from deprecated import deprecated

import classes
import pickle_utils as pkl

def generate_identity(objs, 
                      factors=[],
                      prefix='http://cltl.nl/entity#', 
                      el_filename='',
                      graph_filename=''):
    """
    Decide which entities are identical, based on a set of recognized entity mentions and flexible set of factors.
    """
    data=copy.deepcopy(objs)
    for news_item in data:
        for mention in news_item.sys_entity_mentions:
            mention.identity=pkl.strip_identity(mention.mention)
            #'%s%s' % (prefix, mention.mention)
            if 'docid' in factors:
                mention.identity+=news_item.identifier.split('_')[-1]
            if 'type' in factors:
                mention.identity+=(mention.the_type or '')
                
    with open(el_filename, 'wb') as w:
        pickle.dump(data, w)

    generate_graph(data, graph_filename)

    return data


def replace_identities(news_items_with_entities, new_ids):
    """Store/Replace identity values in the python objects of the entities."""
    for item in news_items_with_entities:
        for e in item.sys_entity_mentions:
            key='%s#%s' % (item.identifier, e.eid)

            new_identity=new_ids[key]
            e.identity=new_identity
    return news_items_with_entities

def construct_m2id(news_items_with_entities):
    """Construct an index of mentions to identities."""
    m2id=defaultdict(set)
    id_num=0
    for item in news_items_with_entities:
        for e in item.sys_entity_mentions:
#            if e.identity.endswith('MISC'): continue
            key='%s#%s' % (item.identifier, e.eid)
            m2id[e.mention].add(key)
    for m, ids in m2id.items():
        id_num+=len(ids)
    print('Identities in m2id', id_num)
    return m2id

@deprecated(reason="Now we are using a different (HAC) clustering algorithm.")
def cluster_matrix(distances, eps=0.1, min_samples=1):
    """Cluster identities of entities based on the DBSCAN algorithm."""
    labels=DBSCAN(min_samples=min_samples, eps=eps, metric='precomputed').fit_predict(distances)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
        
    return list(labels), n_clusters, n_noise

def cluster_identities_dbscan(m2id, wv):
    """Cluster identities for all mentions based on vector similarity and the DBScan algorithm."""
    new_identities={}
    for m, ids in m2id.items():
        num_cands=len(ids)
        if num_cands<2: 
            for i in ids:
                new_identities[i]=i
            continue
        dist_matrix = np.zeros(shape=(num_cands, num_cands)) # Distances matrix
        ids=list(ids)
        for i, ent_i in enumerate(ids):
            for j, ent_j in enumerate(ids):
                if i>j:
                    dist=1-compute_similarity(ent_i, ent_j, wv)
                    dist_matrix[i,j]=dist
                    dist_matrix[j,i]=dist
        clusters, n_clusters, n_noise = cluster_matrix(dist_matrix, eps=0.4)
        for index, cluster_id in enumerate(clusters):
            new_id='%s_%d' % (m, cluster_id)
            old_id=ids[index]
            new_identities[old_id]=new_id
    return new_identities

def cluster_identities(groups, embeddings, max_d=15):
    """Cluster identities for predefined groups based on vector similarity and a hierarchical clustering algorithm."""
    new_identities={}
    for gid, g in enumerate(groups):
        num_cands=len(g)
        if num_cands<2:
            for em in g:
                new_identities[em[1]]=em[1]
            continue
        all_vectors=[]
        for mention, eid in g:
            docid, mention_id = eid.split('#')
            vector=embeddings[docid][mention_id]
            all_vectors.append(vector)
        try:
            l = linkage(all_vectors, method='complete', metric='euclidean')
        except ValueError as e:
            print(all_vectors)
            print(e)
            sys.exit()
        clusters=fcluster(l, max_d, criterion='distance')
        for candidate, c_id in zip(g, clusters):
            old_id=candidate[1]
            new_id='%d_%d' % (gid, c_id)
            new_identities[old_id]=new_id
    return new_identities

def cluster_mention_identities(m2id, embeddings, max_d=15):
    """Cluster identities for all mentions based on vector similarity and a hierarchical clustering algorithm."""
    new_identities={}
    for m, ids in m2id.items():
        num_cands=len(ids)
        if num_cands<2:
            for i in ids:
                new_identities[i]=i
            continue
        all_vectors=[]
        ids=list(ids)
        for mid in ids:
            docid, mention_id = mid.split('#')
            vector=embeddings[docid][mention_id]
            all_vectors.append(vector)
        try:
            l = linkage(all_vectors, method='complete', metric='euclidean')
        except ValueError as e:
            print(all_vectors)
            print(e)
            sys.exit()
        clusters=fcluster(l, max_d, criterion='distance')
        for old_id, c_id in zip(ids, clusters):
            new_id='%s_%d' % (m, c_id)
            new_identities[old_id]=new_id
    return new_identities

def replace_entities(nlp, text, mentions):
    """Replace entity mentions in text with their identity ID."""
    to_replace={}
    for e in mentions:
        start_index=e.begin_index
        end_index=e.end_index
        to_replace[start_index]=pkl.strip_identity(e.identity)
        for i in range(start_index+1, end_index):
            to_replace[i]=''
    doc=nlp(text)
    new_text=[]
    for t in doc:
        idx=t.i
        token=t.text
        if idx in to_replace:
            if to_replace[idx]:
                new_text.append(to_replace[idx])
        else:
            new_text.append(token)
    return ' '.join(new_text)

def generate_graph(data, filename):
    """
    Generate undirected graph, given a collection of news documents.
    """
    G=nx.Graph()
    for news_item in data:
        for mention in news_item.sys_entity_mentions:
            identity=mention.identity
            G.add_node(identity)
            for other_mention in news_item.sys_entity_mentions:
                other_identity=other_mention.identity
                if other_identity>identity:
                    G.add_edge(identity, other_identity)
    print('Identities in the graph', G.number_of_nodes())
    print('Relations in the graph', G.number_of_edges())
    
    nx.write_gpickle(G, filename)

def get_variable_len_combinations(arr):
    """Get combinations of factors with length 0 to len(arr)"""
    res = []
    for l in range(0, len(arr)+1):
        for x in itertools.combinations(arr, l):
            res.append(x)
    return res

def recognize_entities_gold(news_items):
    """Copy the gold entities to system, without the links."""
    for news_item in news_items:
        for e in news_item.gold_entity_mentions:
            e2=copy.deepcopy(e)
            e2.identity=None
            news_item.sys_entity_mentions.append(e2)
    return news_items
    
def recognize_entities_spacy(nlp, news_items):
    """
    Run NER on all documents.
    """
    for i, news_item in enumerate(news_items):
        text=f"{news_item.title}\n{news_item.content}"
        nl_doc=nlp(text)
        ent_id=0
        for sent_i, sent in enumerate(nl_doc.sents):
            for e in sent.ents:
                ent_mention_obj=classes.EntityMention(
                    eid=f"e{ent_id}",
                    mention=e.text,
                    begin_index=e.start,
                    end_index=e.end,
                    the_type=e.label_,
                    sentence=sent_i+1 # since spacy-to-naf indexes sentences from 1
                )
                ent_id+=1
                news_item.sys_entity_mentions.append(ent_mention_obj)
        print(news_item.identifier, len(news_item.sys_entity_mentions))
    return news_items

