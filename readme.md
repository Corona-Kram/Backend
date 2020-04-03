# Corona-Kram Backend


## Requirements

```bash
pip install fastapi
pip install uvicorn
```

## Run

```bash
    uvicorn main:app --reload  # debug mode
```



## Test it out

```bash
    # post 'kram'
    curl -X POST "http://127.0.0.1:8000/kram/" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"name\":\"string\",\"text\":\"string\"}"

    # invalid 'kram
    curl -X POST "http://127.0.0.1:8000/kram/" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"name\":\"string\",\"text\":\"jeg elskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerelskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskererjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerelskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskererjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerelskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskererjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerelskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskererjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerelskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elskerjeg elsker\"}"

    # add phone number
    curl -X POST "http://127.0.0.1:8000/add_number/" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"name\":\"don juan\",\"phone_number\":\"666-666-666\"}"
```