import sys
print("插入前：", sys.path[:3])
sys.path.insert(0, "capstone_kit的绝对路径")
print("插入后：", sys.path[:3])