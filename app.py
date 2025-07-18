from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timezone
import sqlite3
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

app = Flask(__name__)
CORS(app)

def init_db():
    """Initialize the database and create tables"""
    connection = sqlite3.connect("/app/data/bookmarks.db")
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            tags TEXT NOT NULL,
            favicon TEXT NOT NULL,
            createdAt TEXT NOT NULL
        )
    ''')
    connection.commit()
    connection.close()

def get_db_connection():
    """Get a new database connection"""
    connection = sqlite3.connect("/app/data/bookmarks.db")
    connection.row_factory = sqlite3.Row
    return connection

# Initialize database on startup
init_db()

def extract_page_title(url):
    """Extract the title of a webpage from its URL"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        title_tag = soup.find('title')
        
        if title_tag and title_tag.get_text().strip().lower() in ['just a moment...', 'loading...', 'please wait...', '']:
            print(f"Got loading page for {url}, waiting and retrying...")
            time.sleep(2)  # Wait 2 seconds
            
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            title_tag = soup.find('title')
        
        if title_tag:
            title = title_tag.get_text().strip()
            if title.lower() in ['just a moment...', 'loading...', 'please wait...', '']:
                meta_title = soup.find('meta', attrs={'property': 'og:title'})
                if meta_title:
                    return meta_title.get('content', '').strip()
                
                meta_title = soup.find('meta', attrs={'name': 'title'})
                if meta_title:
                    return meta_title.get('content', '').strip()
                
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                return domain.capitalize()
            
            return title
        
        return url
    except Exception as e:
        print(f"Error extracting title from {url}: {e}")
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.capitalize()
        except:
            return url

def generate_favicon_url(url):
    """Generate a Google favicon URL from the domain of the given URL"""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    except Exception as e:
        print(f"Error generating favicon URL for {url}: {e}")
        return "https://www.google.com/s2/favicons?domain=example.com&sz=128"



@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok", "timestamp":  datetime.now(timezone.utc).isoformat()}), 200

@app.route("/api/list")
def list_bookmarks():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM bookmarks')
    rows = cursor.fetchall()
    connection.close()
    
    bookmarks = []
    for row in rows:
        bookmarks.append({
            'id': row['id'],
            'title': row['title'],
            'url': row['url'],
            'tags': json.loads(row['tags']),
            'favicon': row['favicon'],
            'createdAt': row['createdAt']
        })
    
    return jsonify({"status": "success", "bookmarks": bookmarks}), 200

@app.route("/api/delete/<int:bookmark_id>", methods=["DELETE"])
def delete_bookmark(bookmark_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute('SELECT * FROM bookmarks WHERE id = ?', (bookmark_id,))
    bookmark = cursor.fetchone()
    
    if not bookmark:
        connection.close()
        return jsonify({
            "status": "error",
            "message": "bookmark not found"
        }), 404
    
    cursor.execute('DELETE FROM bookmarks WHERE id = ?', (bookmark_id,))
    connection.commit()
    connection.close()
    
    return jsonify({
        "status": "success",
        "message": "bookmark deleted successfully",
        "id": bookmark_id
    }), 200

@app.route("/api/update/<int:bookmark_id>", methods=["PUT"])
def update_bookmark(bookmark_id):
    data = request.json
    connection = get_db_connection()
    cursor = connection.cursor()
    
    cursor.execute('SELECT * FROM bookmarks WHERE id = ?', (bookmark_id,))
    bookmark = cursor.fetchone()
    
    if not bookmark:
        connection.close()
        return jsonify({
            "status": "error",
            "message": "bookmark not found"
        }), 404
    
    current_title = bookmark['title']
    current_url = bookmark['url']
    current_tags = json.loads(bookmark['tags'])
    current_favicon = bookmark['favicon']
    current_createdAt = bookmark['createdAt']
    
    new_title = data.get('title', current_title)
    new_url = data.get('url', current_url)
    new_tags = json.dumps(data.get('tags', current_tags))
    
    if new_url != current_url:
        if not data.get('title'):  # Only extract title if not explicitly provided
            new_title = extract_page_title(new_url)
        new_favicon = generate_favicon_url(new_url)
    else:
        new_favicon = current_favicon
    
    cursor.execute('''
        UPDATE bookmarks 
        SET title = ?, url = ?, tags = ?, favicon = ?
        WHERE id = ?
    ''', (new_title, new_url, new_tags, new_favicon, bookmark_id))
    connection.commit()
    connection.close()
    
    return jsonify({
        "status": "success",
        "message": "bookmark updated successfully",
        "id": bookmark_id,
        "title": new_title,
        "url": new_url,
        "tags": json.loads(new_tags),
        "favicon": new_favicon
    }), 200

@app.route("/api/create", methods=["POST"])
def create_bookmark():
    data = request.json
    url = data.get('url')
    tags = json.dumps(data.get('tags', []))
    createdAt = data.get('createdAt')
    
    title = extract_page_title(url)
    
    favicon = generate_favicon_url(url)
    
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('''
        INSERT INTO bookmarks (title, url, tags, favicon, createdAt)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, url, tags, favicon, createdAt))
    connection.commit()
    bookmark_id = cursor.lastrowid
    connection.close()
    
    return jsonify({
            "status": "success", 
            "message": "bookmark created successfully",
            "id": bookmark_id,
            "title": title,
            "favicon": favicon
        }), 201

@app.route("/api/export")
def export_bookmarks():
    """Export bookmarks as SQL dump"""
    try:
        connection = get_db_connection()
        
        sql_dump = []
        
        sql_dump.append("-- Bookmarks table dump")
        sql_dump.append("-- Generated on: " + datetime.now(timezone.utc).isoformat())
        sql_dump.append("")
        sql_dump.append("CREATE TABLE IF NOT EXISTS bookmarks (")
        sql_dump.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
        sql_dump.append("    title TEXT NOT NULL,")
        sql_dump.append("    url TEXT NOT NULL,")
        sql_dump.append("    tags TEXT NOT NULL,")
        sql_dump.append("    favicon TEXT NOT NULL,")
        sql_dump.append("    createdAt TEXT NOT NULL")
        sql_dump.append(");")
        sql_dump.append("")
        
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM bookmarks ORDER BY id')
        rows = cursor.fetchall()
        
        if rows:
            sql_dump.append("-- Insert bookmarks data")
            for row in rows:
                title = row['title'].replace("'", "''")
                url = row['url'].replace("'", "''")
                tags = row['tags'].replace("'", "''")
                favicon = row['favicon'].replace("'", "''")
                createdAt = row['createdAt'].replace("'", "''")
                
                insert_sql = f"INSERT INTO bookmarks (id, title, url, tags, favicon, createdAt) VALUES ({row['id']}, '{title}', '{url}', '{tags}', '{favicon}', '{createdAt}');"
                sql_dump.append(insert_sql)
        else:
            sql_dump.append("-- No bookmarks found")
        
        connection.close()
        
        sql_content = "\n".join(sql_dump)
        
        response = jsonify({
            "status": "success",
            "message": "Bookmarks exported successfully",
            "sql_dump": sql_content,
            "export_date": datetime.now(timezone.utc).isoformat(),
            "total_bookmarks": len(rows) if rows else 0
        })
        
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename="bookmarks_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql"'
        
        return response, 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Export failed: {str(e)}"
        }), 500

@app.route("/api/restore", methods=["POST"])
def restore_bookmarks():
    """Restore bookmarks from SQL dump"""
    try:
        data = request.json
        sql_dump = data.get('sql_dump')
        
        if not sql_dump:
            return jsonify({
                "status": "error",
                "message": "No SQL dump provided"
            }), 400
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Split the SQL dump into individual statements
        statements = [stmt.strip() for stmt in sql_dump.split(';') if stmt.strip()]
        
        executed_statements = 0
        imported_bookmarks = 0
        
        # Execute each statement
        for statement in statements:
            if statement.strip():
                try:
                    # Skip comments
                    if statement.strip().startswith('--'):
                        continue
                    
                    cursor.execute(statement)
                    executed_statements += 1
                    
                    # Count INSERT statements for bookmarks
                    if statement.upper().strip().startswith('INSERT INTO BOOKMARKS'):
                        imported_bookmarks += 1
                        
                except sqlite3.Error as e:
                    # If it's a table already exists error, continue
                    if "already exists" in str(e).lower():
                        continue
                    else:
                        connection.rollback()
                        connection.close()
                        return jsonify({
                            "status": "error",
                            "message": f"SQL execution error: {str(e)}",
                            "failed_statement": statement[:100] + "..." if len(statement) > 100 else statement
                        }), 500
        
        connection.commit()
        connection.close()
        
        return jsonify({
            "status": "success",
            "message": "Bookmarks restored successfully",
            "executed_statements": executed_statements,
            "imported_bookmarks": imported_bookmarks,
            "restore_date": datetime.now(timezone.utc).isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Restore failed: {str(e)}"
        }), 500

@app.route("/api/tags")
def get_tags():
    """Get all unique tags from bookmarks in alphabetical order"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT tags FROM bookmarks')
        rows = cursor.fetchall()
        connection.close()
        
        all_tags = set()
        for row in rows:
            try:
                tags = json.loads(row['tags'])
                if isinstance(tags, list):
                    all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                continue
        
        sorted_tags = sorted(list(all_tags))
        
        return jsonify({
            "status": "success",
            "tags": sorted_tags,
            "total_tags": len(sorted_tags)
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve tags: {str(e)}"
        }), 500

@app.route("/help")
def help():
    """
    Provides API usage information with examples for each endpoint.
    """
    help_info = {
        "endpoints": [
            {
                "path": "/api/health",
                "method": "GET",
                "description": "Check service health",
                "example_request": "GET /api/health",
                "example_response": {"status": "ok", "timestamp": "2025-07-12T12:34:56Z"}
            },
            {
                "path": "/api/list",
                "method": "GET",
                "description": "List all bookmarks",
                "example_request": "GET /api/list",
                "example_response": {"status": "success", "bookmarks": []}
            },
            {
                "path": "/api/create",
                "method": "POST",
                "description": "Create a new bookmark",
                "example_request": "POST /api/create with JSON body {'url': 'http://example.com', 'tags': ['tag1']}" ,
                "example_response": {"status": "success", "message": "bookmark created successfully", "id": 1, "title": "Example", "favicon": "https://..."}
            },
            {
                "path": "/api/update/<id>",
                "method": "PUT",
                "description": "Update an existing bookmark",
                "example_request": "PUT /api/update/1 with JSON body {'title': 'New Title'}",
                "example_response": {"status": "success", "message": "bookmark updated successfully", "id": 1, "title": "New Title"}
            },
            {
                "path": "/api/delete/<id>",
                "method": "DELETE",
                "description": "Delete a bookmark",
                "example_request": "DELETE /api/delete/1",
                "example_response": {"status": "success", "message": "bookmark deleted successfully", "id": 1}
            },
            {
                "path": "/api/export",
                "method": "GET",
                "description": "Export bookmarks as SQL dump",
                "example_request": "GET /api/export",
                "example_response": {"status": "success", "sql_dump": "...", "total_bookmarks": 0}
            },
            {
                "path": "/api/tags",
                "method": "GET",
                "description": "Get all unique tags from bookmarks in alphabetical order",
                "example_request": "GET /api/tags",
                "example_response": {"status": "success", "tags": ["docs", "inspiration", "icons"], "total_tags": 3}
            },
            {
                "path": "/api/restore",
                "method": "POST",
                "description": "Restore bookmarks from SQL dump",
                "example_request": "POST /api/restore with JSON body {'sql_dump': 'CREATE TABLE...; INSERT INTO...;'}",
                "example_response": {"status": "success", "message": "Bookmarks restored successfully", "imported_bookmarks": 5}
            }
        ]
    }
    return jsonify(help_info), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5570)