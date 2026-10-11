def _r006_cases():
    """★ 供 B/C 两项：**用本工具真实判据造合成输入**（替换通用块的占位实现）。

    ★ 依据：本工具四检的红项判定（`red.append(...)`），其中「幂等：两次跑结果不一致」最易构造：
      ⇒ B 项：**离幂等的脚本 ⇒ 两次输出必须不同**（判据能红）
      ⇒ C 项：**干净幂等脚本 ⇒ 两次输出逐字节一致**（判据不误伤）

    ★★ 一处**必须记住的实现事实**（我踩过）：
       `run_once()` 用 `argv = [sys.executable, script]` 执行 ⇒
       **本沙箱只适用于 Python 脚本**（**bash 脚本会被当 Python 跑而报 SyntaxError**，
       表现为 `exit=1` 且 `err` 里是 Python traceback）。
       ⇒ 故本函数的合成样例**一律用 Python 写**。

    ★ 为何不用「写受保护路径」作负例：**那会真写文件** ——
      本门原则是「只读探测 + 临时目录」，故负例选**离幂等**这种**无副作用**形态。
    ★ 两次跑都是真跑（`run_once`），结论取自**它自己的返回**，非另起一套判据。
    """
    _tmp = tempfile.mkdtemp(prefix="sdg-r006-")
    # ── B 负例：输出随机数 ⇒ 两次跑不同 ⇒ 离幂等 ──
    _neg = os.path.join(_tmp, "nonidem.py")
    with open(_neg, "w") as f:
        f.write("import random" + chr(10) + "print('probe-%r' % random.random())" + chr(10))
    _n1 = run_once(_neg, [], _tmp, None, 20)
    _n2 = run_once(_neg, [], _tmp, None, 20)
    # ── C 正例：固定输出 ⇒ 两次跑逐字节一致（幂等的定义）──
    _pos = os.path.join(_tmp, "clean.py")
    with open(_pos, "w") as f:
        f.write("print('ok')" + chr(10))
    _p1 = run_once(_pos, [], _tmp, None, 20)
    _p2 = run_once(_pos, [], _tmp, None, 20)

    b = [
        ("离幂等脚本 ⇒ 两次输出**不同**（out1=%s / out2=%s）"
         % (str(_n1.get("out"))[:20], str(_n2.get("out"))[:20]),
         _n1.get("out") != _n2.get("out") and _n1.get("exit") == 0, True),
    ]
    c = [
        ("干净幂等脚本 ⇒ 两次输出**逐字节一致**且 exit=0（out=%s）" % str(_p1.get("out"))[:20],
         _p1.get("out") == _p2.get("out") and _p1.get("exit") == 0, True),
    ]
    return b, c
