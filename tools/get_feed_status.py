from app.dhan.live_feed import get_live_feed_status

if __name__ == '__main__':
    import json
    print(json.dumps(get_live_feed_status(), indent=2, default=str))
