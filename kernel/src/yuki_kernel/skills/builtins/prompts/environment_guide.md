在生成或执行 shell 命令前，如果上下文里已有 get_environment_info 返回的环境信息
（操作系统、Python 版本、当前工作目录），直接使用，不要重复调用；没有时再调用
get_environment_info 获取，再根据实际环境生成命令。
