from time import sleep


def run_sleep(time:int):
    if not time:
       return "错误：请输入等待时间"
    else:
        sleep(time)
        return f"等待：{time}s"
