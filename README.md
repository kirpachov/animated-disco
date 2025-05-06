# File uploader
Completely written by Deepseek.

## Usage
```bash
docker build -t file-uploader . && docker run -p 8080:80 -v $(pwd)/app/uploads:/app/uploads file-uploader
```

## TODO
- More clean interface on upload page: does not reload after success