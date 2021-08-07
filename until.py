import sys
import dis

def Until(exc):
    frame = sys._getframe(1)
    f_code = frame.f_code
    cur_pos = frame.f_lasti
    if len(f_code.co_code) >= cur_pos + 2 \
        and f_code.co_code[cur_pos + 2] == dis.opmap['POP_JUMP_IF_FALSE']:
        end_pos = f_code.co_code[cur_pos + 3] - 2
        start_pos = f_code.co_code[end_pos + 1]
    else:
        return
    dis.dis(f_code)
    print(cur_pos, start_pos, end_pos)
