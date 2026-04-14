import config
from runners import RUNNER_MAP

def main():
    mode = config.RUNNER_MODE
    print(f"--- Runner Mode: {mode.upper()} ---")
    
    runner_class = RUNNER_MAP.get(mode)
    if runner_class:
        runner_class(config).run()
    else:
        raise ValueError(f"Unknown Mode: '{mode}'.")

if __name__ == "__main__":
    main()