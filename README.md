# File uploader
Completely written by Deepseek.

## Usage
```bash
docker build -t file-uploader . && docker run -p 8080:80 -v $(pwd)/app/uploads:/app/uploads file-uploader
```

## TODO
- Upload page should reload after successful upload
- run docker with current user permissions to avoid messing with permissions
- build and push image to dockerhub on push of this repo
