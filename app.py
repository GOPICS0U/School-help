# Étape 1 : Configurer l'API YouTube pour récupérer les vidéos
# Importation des bibliothèques nécessaires
import requests
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from threading import Lock

# Remplacez par votre propre clé API YouTube
API_KEY = 'AIzaSyAdyl0jFZUsixxPlW8H-_mCbnonRLqVfJo'
BASE_URL = 'https://www.googleapis.com/youtube/v3/search'

# Initialiser l'application Flask
app = Flask(__name__)

# Initialiser la base de données locale et un verrou pour éviter les conflits d'accès
conn = sqlite3.connect('videos.db', check_same_thread=False)
cursor = conn.cursor()
db_lock = Lock()

# Création de la table si elle n'existe pas déjà
with db_lock:
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        thumbnail_url TEXT,
        video_url TEXT,
        category TEXT
    )
    ''')
    conn.commit()

# Fonction pour récupérer des vidéos basées sur des mots-clés
def fetch_youtube_videos(query, max_results=10):
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'videoCaption': 'closedCaption',  # Optionnel, pour des vidéos avec sous-titres
        'maxResults': max_results,
        'key': API_KEY
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()  # Lève une exception en cas d'erreur HTTP
        return response.json().get('items', [])
    except requests.RequestException as e:
        print(f"Erreur lors de la requête YouTube API : {e}")
        return []

# Sauvegarder les vidéos dans la base de données
def save_video_to_db(video_id, title, description, thumbnail_url, video_url, category):
    with db_lock:
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO videos (id, title, description, thumbnail_url, video_url, category)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (video_id, title, description, thumbnail_url, video_url, category))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Erreur lors de l'insertion dans la base de données : {e}")

# Route principale pour afficher les vidéos sauvegardées
@app.route('/')
def index():
    with db_lock:
        cursor.execute('SELECT * FROM videos')
        saved_videos = cursor.fetchall()
    return render_template('index.html', saved_videos=saved_videos)

# Route pour rechercher des vidéos sur YouTube
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('query')
        category = request.form.get('category', 'Autres')

        # Récupérer les vidéos depuis l'API YouTube
        videos = fetch_youtube_videos(query)

        return render_template('search.html', videos=videos, category=category)
    return render_template('search.html', videos=[], category='')

# Route pour ajouter une vidéo aux favoris
@app.route('/add_to_favorites', methods=['POST'])
def add_to_favorites():
    video_id = request.form.get('video_id')
    title = request.form.get('title')
    description = request.form.get('description')
    thumbnail_url = request.form.get('thumbnail_url')
    video_url = request.form.get('video_url')
    category = request.form.get('category')

    # Sauvegarder la vidéo dans la base de données
    save_video_to_db(video_id, title, description, thumbnail_url, video_url, category)

    return redirect(url_for('index'))

# Route pour supprimer une vidéo des favoris
@app.route('/remove_from_favorites', methods=['POST'])
def remove_from_favorites():
    video_id = request.form.get('video_id')

    with db_lock:
        try:
            cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Erreur lors de la suppression de la vidéo : {e}")

    return redirect(url_for('index'))

# Exemple de récupération et de sauvegarde des vidéos si exécuté en standalone
if __name__ == '__main__':
    try:
        app.run(debug=True)
    finally:
        conn.close()  # Assure une fermeture propre de la connexion
