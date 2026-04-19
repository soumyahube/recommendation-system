# export_fixed.py
import pandas as pd
import subprocess
import os
import time
import sys
from sqlalchemy import create_engine, text  # AJOUT: text

def export_with_ram_safety():
    """Export optimisé pour 3.2GB RAM"""
    
    print("🚀 EXPORT OPTIMISÉ POUR 3.2GB RAM")
    print("=" * 60)
    
    # Paramètres
    CHUNK_SIZE = 60000
    
    # Connexion PostgreSQL
    engine = create_engine('postgresql://admin:admin123@localhost:5432/movierec')
    
    # Vérifier le total - SYNTAXE CORRIGÉE
    with engine.connect() as conn:
        # CORRECTION: Utiliser text() pour les requêtes SQL
        result = conn.execute(text("SELECT COUNT(*) FROM fact_ratings"))
        total_rows = result.scalar()
        print(f"📊 Total à exporter: {total_rows:,} lignes")
    
    offset = 0
    chunk_num = 0
    total_exported = 0
    
    print(f"\n🎯 Configuration:")
    print(f"   • Chunk size: {CHUNK_SIZE:,} lignes")
    print(f"   • RAM disponible: 3.2 GB")
    print(f"\n⏳ Début de l'export...")
    
    start_time = time.time()
    
    # Créer dossiers Google Drive
    subprocess.run(["rclone", "mkdir", "gdrive:movie_data_25m"], capture_output=True)
    subprocess.run(["rclone", "mkdir", "gdrive:movie_data_25m/chunks"], capture_output=True)
    
    try:
        while True:
            # Requête - SYNTAXE CORRIGÉE
            query = text(f"""
                SELECT rating_id, user_key, movie_key, rating
                FROM fact_ratings 
                ORDER BY rating_id 
                LIMIT {CHUNK_SIZE} OFFSET {offset}
            """)
            
            # Lire chunk - CORRECTION: utiliser text() dans read_sql
            df = pd.read_sql(query, engine.connect())
            
            if len(df) == 0:
                print("\n✅ Plus de données")
                break
            
            # Optimiser types
            for col in ['rating_id', 'user_key', 'movie_key']:
                if col in df.columns:
                    df[col] = df[col].astype('int32')
            if 'rating' in df.columns:
                df['rating'] = df['rating'].astype('float32')
            
            # Sauvegarder dans RAM
            temp_file = f"/dev/shm/chunk_{chunk_num:05d}.csv.gz"
            df.to_csv(temp_file, index=False, compression='gzip')
            
            file_size_mb = os.path.getsize(temp_file) / (1024**2)
            total_exported += len(df)
            
            # Upload
            print(f"📦 {chunk_num:03d}: {len(df):,}l → {file_size_mb:.1f}MB → ", end="", flush=True)
            
            try:
                result = subprocess.run(
                    ["rclone", "copyto", temp_file, 
                     f"gdrive:movie_data_25m/chunks/chunk_{chunk_num:05d}.csv.gz"],
                    capture_output=True,
                    text=True,
                    timeout=45
                )
                print("Google Drive ✓" if result.returncode == 0 else "❌")
            except Exception as e:
                print(f"⏱️ {str(e)[:20]}")
            
            # Supprimer immédiatement
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            
            # Mettre à jour
            offset += CHUNK_SIZE
            chunk_num += 1
            
            # Progression
            if chunk_num % 5 == 0:
                elapsed = time.time() - start_time
                percent = (total_exported / total_rows) * 100
                rate = total_exported / elapsed if elapsed > 0 else 0
                
                # ETA
                remaining = total_rows - total_exported
                if rate > 0:
                    eta_seconds = remaining / rate
                    eta_hours = eta_seconds / 3600
                    print(f"   • {total_exported:,}l [{percent:.1f}%] - {rate:,.0f}l/s")
                    print(f"   • ETA: {eta_hours:.1f}h restantes")
                else:
                    print(f"   • {total_exported:,}l [{percent:.1f}%]")
            
            # Libérer mémoire
            del df
            
            # Pause occasionnelle pour éviter surcharge
            if chunk_num % 50 == 0:
                import gc
                gc.collect()
                time.sleep(2)
                
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrompu - {total_exported:,} lignes exportées")
    
    finally:
        engine.dispose()
    
    # Rapport final
    total_time = time.time() - start_time
    
    print(f"\n" + "=" * 60)
    print("✅ EXPORT TERMINÉ !")
    print("=" * 60)
    print(f"📊 Résultats:")
    print(f"   • Lignes: {total_exported:,}")
    print(f"   • Chunks: {chunk_num}")
    print(f"   • Temps: {total_time/3600:.1f} heures")
    
    if total_time > 0:
        print(f"   • Vitesse: {total_exported/total_time:,.0f} l/s")
    
    # Vérifier Google Drive
    print(f"\n🔍 Google Drive:")
    try:
        result = subprocess.run(["rclone", "lsf", "gdrive:movie_data_25m/chunks/"], 
                              capture_output=True, text=True)
        files = [f for f in result.stdout.strip().split('\n') if f]
        print(f"   • Fichiers: {len(files)}/{chunk_num}")
    except:
        print(f"   • Vérification échouée")
    
    print("\n🎯 DONNÉES DISPONIBLES SUR GOOGLE DRIVE !")
    print("=" * 60)

if __name__ == "__main__":
    print("🎬 EXPORT MOVIELENS 25M")
    print("=" * 60)
    
    # Vérifier imports
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "sqlalchemy"])
        from sqlalchemy import create_engine, text
    
    # Lancer
    export_with_ram_safety()