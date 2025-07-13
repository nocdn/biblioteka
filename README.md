# Biblioteka

> flask application for managing bookmarks with a simple API.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/nocdn/biblioteka.git
   cd biblioteka
   ```

2. Create and activate a virtual environment:

   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   uv pip install -r requirements.txt
   ```

## Running in Docker

```bash
docker build -t biblioteka-img .
docker run --name biblioteka --restart always -p 5570:5570 -v biblioteka-data:/app/data biblioteka-img
```

## Running for Development

Start the server locally:

```bash
python app.py
```

By default, the app will run on `http://localhost:5570`.

## API Usage

### Health Check

```bash
curl http://localhost:5570/api/health
```

#### Example Response

```json
{
  "status": "ok",
  "timestamp": "2025-07-12T12:34:56Z"
}
```

### List Bookmarks

```bash
curl http://localhost:5570/api/list
```

#### Example Response

```json
{
  "status": "success",
  "bookmarks": []
}
```

### Create a Bookmark

```bash
curl -X POST http://localhost:5570/api/create \
  -H "Content-Type: application/json" \
  -d '{"url":"http://example.com","tags":["tag1","tag2"],"createdAt":"2025-07-12T12:00:00Z"}'
```

#### Example Response

```json
{
  "status": "success",
  "message": "bookmark created successfully",
  "id": 1,
  "title": "Example",
  "favicon": "https://www.google.com/s2/favicons?domain=example.com&sz=128"
}
```

### Update a Bookmark

```bash
curl -X PUT http://localhost:5570/api/update/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"New Title","tags":["tag3"]}'
```

#### Example Response

```json
{
  "status": "success",
  "message": "bookmark updated successfully",
  "id": 1,
  "title": "New Title",
  "url": "http://example.com",
  "tags": ["tag3"],
  "favicon": "https://www.google.com/s2/favicons?domain=example.com&sz=128"
}
```

### Delete a Bookmark

```bash
curl -X DELETE http://localhost:5570/api/delete/1
```

#### Example Response

```json
{
  "status": "success",
  "message": "bookmark deleted successfully",
  "id": 1
}
```

### Export Bookmarks

```bash
curl http://localhost:5570/api/export
```

#### Example Response

```json
{
  "status": "success",
  "message": "Bookmarks exported successfully",
  "sql_dump": "-- Bookmarks table dump...",
  "export_date": "2025-07-12T12:34:56Z",
  "total_bookmarks": 0
}
```

### Help

```bash
curl http://localhost:5570/help
```

#### Example Response

```json
{
  "endpoints": [
    /* see detailed list of endpoints and examples */
  ]
}
```
