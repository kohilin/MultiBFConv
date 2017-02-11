#!/usr/bin/env python
# -*- coding:utf-8 -*-

import re
import sys


class Conllu:
    def __init__(self, id, form, lemma, upostag, xpostag, feats, head, deprel, deps, misc):
        self.mId = id
        self.mForm = form
        self.mLemma = lemma
        self.mUpostag = upostag
        self.mXpostag = xpostag
        self.mFeats = feats
        self.mHead = head
        self.mDeprel = deprel
        self.mDeps = deps
        self.mMisc = misc
        self.mParent = head
        self.mLeftChild = []
        self.mRightChild = []



    def print_all(self, delimiter="\t"):
        print((self.mId + delimiter + self.mForm + delimiter + self.mLemma + delimiter + self.mUpostag + delimiter + self.mXpostag + delimiter + self.mFeats + delimiter + self.mHead + delimiter + self.mDeprel + delimiter + self.mDeps + delimiter + self.mMisc).strip())

class Sentence:
    def __init__(self):
        self.sentence = []
        self.proj = 1

def create_tree(sentence):
    for i, c in enumerate(sentence):
        assert isinstance(c, Conllu)
        head = int(c.mHead) - 1

        if head != -1:
            if i < int(sentence[head].mId):
                sentence[head].mLeftChild.append(i)
            else:
                sentence[head].mRightChild.append(i)
    return sentence


def check_proj(sentence):
    for i, c in enumerate(sentence):
        assert isinstance(c, Conllu)

        headId = int(c.mHead)
        childId = int(c.mId)
        if c.mHead == 0 or abs(headId - childId) == 1:
            continue


        if headId > childId:
            for i in range(childId, headId-1):
                if int(sentence[i].mHead) < int(c.mId) or int(sentence[i].mHead) > int(c.mHead):
                    return 0
        else:
            for i in range(headId, childId-1):
                if int(sentence[i].mHead) < int(c.mHead) or int(sentence[i].mHead) > int(c.mId):
                    return 0
    return 1



def conllu_reader(conllufile):
    sentences = []
    sentence = Sentence()
    with open(conllufile) as f:
        for line in f:
            if re.match("\n", line):
                sentences.append(create_tree(sentence.sentence))
                sentence = Sentence()
            else:
                [id, form, lemma, upostag, xpostag, feats, head, deprel, deps, misc] = line.split('\t')
                word = Conllu(id, form, lemma, upostag, xpostag, feats, head, deprel, deps, misc)
                sentence.sentence.append(word)

    return sentences


class MultiBFConv:
    def __init__(self):
        """
            Modify here to change conversion targets

            e.g.
                only change "ADP case" and "ADP "mark"
                self.target = [ ["ADP", "case"],
                                ["ADP", "mark"]]

        """
        self.target = [["ADP", "case"],
                       ["ADP","mark"],
                       ["ADP", "dep"],
                       ["SCONJ","mark"],
                       ["ADV","mark"],
                       ["PART","case"],
                       ["PART","mark"]]

    # Forward functions

    def convert_forward(self, parent_idx, sentence):
        p = sentence[parent_idx]
        [self.convert_forward(child, sentence) for child in p.mLeftChild]
        target = self.search_forward(p.mLeftChild, sentence)
        if target is not -1: self.change_dep_forward(target, p)

        """
            Updating dependencies after modification in forward processing makes a function word climb up tree

            e.g.
                I heard Mika lives in Tokyo

                live -> Tokyo
                Tokyo -> in

                1st step
                    p: Tokyo target: in
                    in -> Tokyo
                    live -> in

                if update live's children from Tokyo to in ...

                2nd step
                    p: live "target: in"
                    in -> live
                    heard -> in

                This is not what we want to do

        """
        # self.modifyDependency([sentence[c] for c in p.mLeftChild], p, sentence, "F", "L")


        [self.convert_forward(child, sentence) for child in p.mRightChild]
        target = self.search_forward(reversed(p.mRightChild), sentence)
        if target is not -1: self.change_dep_forward(target, p)
        # self.modifyDependency([sentence[c] for c in p.mRightChild], p, sentence, "F", "R")



    def change_dep_forward(self, child, parent):
        if parent.mDeprel != "root":
            child.mHead = parent.mHead
            parent.mHead = child.mId

    def search_forward(self, children, sentence):
        for child in children:
            c = sentence[child]
            if [c.mUpostag, c.mDeprel] in self.target:
                return c
        return -1


    ### Backward functions

    def convert_backward(self, parent_idx, sentence):
        p = sentence[parent_idx]
        [self.convert_backward(child, sentence) for child in p.mLeftChild]
        lc = [sentence[c] for c in p.mLeftChild if sentence[c].mDeprel != "mwe"]

        """
            In backward process, on the contrary, updating children makes reconverting accuracy slightly higher
            This operation is for a continuous function arcs (see below), nothing changes for other results as far as I see

                e.g.
                    ... spot for  a real Hackney 's is  Printers ...

                    spot ->(case) for // continuous
                    for ->(case) 's   //  continuous
                    's -> Hackney

            First this algorithm modifies depth one

                    (BEFORE) 's -> Hackney
                              for -> 's

                    (AFTER)  Hackney -> 's
                             for -> Hackney

            But variable lc in previous recursive step still remains with

                    for -> 's

            so that rewrite it with a "new" head of original child

                    for -> Hackney

        """

        lc = self.modifyDependency(lc, p, sentence, "B", "L")
        if [p.mUpostag, p.mDeprel] in self.target and len(lc) > 0:
            self.change_dep_backward(lc, p, lc[0])


        [self.convert_backward(child, sentence) for child in p.mRightChild]
        rc = [sentence[c] for c in p.mRightChild if sentence[c].mDeprel != "mwe"]
        rc = self.modifyDependency(rc, p, sentence, "B", "R")
        if [p.mUpostag, p.mDeprel] in self.target and len(rc) > 0:
            self.change_dep_backward(rc, p, rc[-1])


    def change_dep_backward(self, children, parent, top):
            for c in children:
                c.mHead = parent.mHead

                """

                    In backward conversion with predicted trees, there are some cases where a function word has multi children.

                    e.g.
                        ... provides in a single glass all four essential groups ...

                        provides -> in

                        in -> glass
                        in -> groups (incorrect prediction)

                    Then replace heads of those content words with a head of function word (provides, in this case).

                        provides -> glass
                        provides -> groups (incorrect prediction)

                    And replace a head of a function word with an index of an "innermost" (i.e. rightmost for left children, leftmost for rightchildren) child word (glass, in this case),
                    because an arc between near words is basically more popular than father one.

                        glass -> in

                    In original UD, it is very rare situation where function word has children other than mwe components,
                    therefore, basically function words after forward conversion also have only one child which is originally their head.

                """

            parent.mHead = top.mId


    def modifyDependency(self, children, parent, sentence, type, side):
        for child in children:
            if child.mHead != parent.mId:
                if type is "F":
                    self.fixDependency(sentence[int(child.mHead)-1], child, parent)
                else:
                    self.fixDependency(parent, sentence[int(child.mHead)-1], child)

        lc = [sentence[c] for c in parent.mLeftChild if sentence[c].mDeprel != "mwe"]
        rc = [sentence[c] for c in parent.mRightChild if sentence[c].mDeprel != "mwe"]
        return lc if side is "L" else rc



    def fixDependency(self, top, mid, buttom):
        if int(top.mId) < int(buttom.mId):
            top.mRightChild.remove(int(buttom.mId) - 1)
        else:
            top.mLeftChild.remove(int(buttom.mId) - 1)

        if int(top.mId) < int(mid.mId):
            top.mRightChild.append(int(mid.mId) - 1)
        else:
            top.mLeftChild.append(int(mid.mId) - 1)







if __name__ == "__main__":
    sentences = conllu_reader(sys.argv[1])
    converter = MultiBFConv()
    for i,sentence in enumerate(sentences):
        for word in sentence:
            if word.mDeprel == "root":
                if sys.argv[2] == "forward":
                    converter.convert_forward(int(word.mId) - 1, sentence)
                elif sys.argv[2] == "backward":
                    converter.convert_backward(int(word.mId) - 1, sentence)
                else:
                    raise Exception("you have to choose \"forward\" or \"backward\" for second argument")

            else:
                pass

    for sentence in sentences:
        for word in sentence:
            word.print_all()
        print()
