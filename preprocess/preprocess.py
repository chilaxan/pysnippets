import sys, dis, subprocess
frame = sys._getframe()
while frame := frame.f_back:
    f_code = frame.f_code
    if f_code.co_code[frame.f_lasti] == dis.opmap['IMPORT_NAME'] \
        and f_code.co_names[f_code.co_code[frame.f_lasti + 1]] == 'preprocess':
        file = frame.f_globals['__file__']
        if file:
            processed = subprocess.run(['gcc', '-E','-x','c', file], stdout=subprocess.PIPE)
            if processed.returncode == 0:
                exec(processed.stdout.decode())
            exit(processed.returncode)
