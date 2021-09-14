def p(s,j=''.join,T=(()for()in()).throw,e=Exception):
    a=lambda s,c,m:n if s and (n:=s.pop())in c else T(e(m))
    S=lambda s:s.__setitem__(slice(None), j(s).rstrip())or s
    if isinstance(s, str):
        return T(e('Extra Data Remaining')) if [r:=p(s:=[*s[::-1]])] and j(s).rstrip() else r
    if (S(s)[-1].isdecimal() or s[-1] in '-+.') if s else T(e('Not Enough Data')):
        return int(v)if(v:=j([s.pop()for(_)in iter(lambda:len(s)and(s[-1].isdecimal()or s[-1]in'.Ee-+'),0)]))[v[0]in'-+':].isdecimal()else float(v)
    elif s[-1] in 'tfn':
        return [v:={'true':True,'false':False,'null':None}.get(j(iter(lambda:len(s)and s[-1].isalnum()and s.pop(),0)),2),v!=2or T(e('Invalid Constant'))][0]
    t=']}"'[(d:=ord(a(s, '{["', 'Invalid JSON'))//2%3)]
    r=[[],{},""][d]
    while (s and s[-1] != t and [k:=S(s) and p(s)if d<2 else s.pop()]):
        if [(r.append(k)or S(s)) \
                if d==0 else \
            (a(s,':','Invalid Seperator in Object')and r.update({k:p(s)})or S(s) \
                if isinstance(k, str)else \
            T(e('Object Keys must be Strings')))\
                if d==1 else \
            (r:=r+(k \
                if k!='\\'else \
            ('\b\f\n\r\t'+q)[('bfnrt'+q).index(q)] \
                if(q:=a(s,r'\"bfnrtu','Invalid Escape Specifier'))!='u'else \
            T(e('Not Enough Characters Following \\u')) \
                if len(s)<=4else \
            chr(int(C,16)) \
                if all(map('0123456789abcdefABCDEF'.count,C:=j(s.pop()for(_)in range(4))))else \
            T(e('Invalid Codepoint')))) \
                if d==2 else \
            0] and d<2 and (a(s,','+t,'Missing Terminator or Seperator')==t):
                break
    else:
        a(s, t, 'Missing Terminator')
    return r

p=lambda s,j=''.join:({}['Extra Data Remaining']if[r:=p(I:=[*s][::-1])]and j(I).rstrip()else r)if isinstance(s,str)else float(i)if(S:=lambda s:s.__setitem__(slice(None),j(s).rstrip())or s)(s)and(i:=j(iter(lambda:s.pop()if s and s[-1]in'-+0123456789.eE'else 0,0)))else{'true':True,'false':False,'null':None}[c]if(c:=j(iter(lambda:s.pop()if s and s[-1].isalpha()else 0,0)))else[list,dict,j][(d:=ord(s.pop())//2%3)](iter(lambda:(s.pop()and p)if S(s)[-1]==(t:=']}"'[d])else[k if[k:=p(s)if d<2else s.pop()]and d==0else((k if isinstance(k,str)else{}['Keys must be Strings'],p(s))if d==1and(S(s),{}['Invalid Seperator']if s[-1]!=':'else s.pop())else(k if k!='\\'else('\b\f\n\r\t'+q)[('bfnrt'+q).index(q)]if(q:=s.pop())!='u'else chr(int(j(s.pop()for()in[()]*4),16)))if d==2else p),(s.pop()if l!=t else 0)if d<2and(l:=S(s)[-1])in','+t else 0if d==2else{}['Missing Seperator']][0],p))
