import config
from runners import get_runner

def main():
    mode = config.RUNNER_MODE
    print(f"--- Runner Mode: {mode.upper()} ---")
    
    try:
        runner = get_runner(mode, config)
        runner.run()
        
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
if __name__ == "__main__":
    main()