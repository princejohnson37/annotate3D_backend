# AAT Backend

## Create virtual env

```bash
$ python -m venv env
$ ./env/scripts/activate
```
or
to create conda env
```bash
$ conda create --name aat_backend python=3.10
$ conda activate aat_backend

```

to activate existing conda env
```bash
$ conda info --envs
$ conda activate <env_name>
```

## Install requirements

```bash
$ pip install -r requirements.txt
```

## Initialize database
```bash
$ alembic upgrade head
```

## Run the backend

```bash
$ uvicorn aat_backend.main:app --host 0.0.0.0 --workers 4 --reload 
```
