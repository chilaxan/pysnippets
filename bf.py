def bf(inp,i=0,p=0,t={},s=open(0)):
    while i<len(inp):
        match inp[i]:
            case '>':
                p+=1
            case '<':
                p-=1
            case '+':
                t[p]=t.get(p,0)+1
            case '-':
                t[p]=t.get(p,0)-1
            case '.':
                print(end=chr(t.get(p,0)))
            case ',':
                t[p]=ord(s.read(1))
            case '[':
                if t[p]:i+=bf(inp[i+1:]);continue
            case ']':
                if t[p]!=0:return i
                else:return 0
        i+=1

p="++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."