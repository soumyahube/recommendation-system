# convert_with_quota_management.py
import pandas as pd
import subprocess
import io
import gzip
import time
import gc

def convert_with_quota():
    """Convertit avec gestion de quota Google Drive"""
    
    print("🔄 CONVERSION AVEC GESTION DE QUOTA")
    print("=" * 60)
    
    # 1. Lister les fichiers
    print("📋 Listing des fichiers...")
    result = subprocess.run(
        ["rclone", "lsf", "gdrive:movie_data_25m/chunks/"],
        capture_output=True,
        text=True
    )
    
    files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
    print(f"   • {len(files)} fichiers trouvés")
    
    # 2. Vérifier ce qui est déjà converti
    print("🔍 Vérification des fichiers déjà convertis...")
    result = subprocess.run(
        ["rclone", "lsf", "gdrive:movie_data_25m/parquet/"],
        capture_output=True,
        text=True
    )
    
    converted = [f.strip() for f in result.stdout.split('\n') if f.strip()]
    converted_names = [f.replace('.parquet', '') for f in converted]
    
    # 3. Filtrer
    to_convert = []
    for f in files:
        if f.replace('.csv.gz', '') not in converted_names:
            to_convert.append(f)
    
    print(f"   • Déjà convertis: {len(converted)}")
    print(f"   • Reste à convertir: {len(to_convert)}")
    
    if not to_convert:
        print("\n✅ TOUT EST DÉJÀ CONVERTI!")
        return
    
    # 4. Créer dossier Parquet
    subprocess.run(["rclone", "mkdir", "gdrive:movie_data_25m/parquet/"], capture_output=True)
    
    # 5. Conversion avec pauses pour éviter quota
    print(f"\n🔄 Conversion de {len(to_convert)} fichiers avec gestion quota...")
    
    start_time = time.time()
    success = 0
    failed = 0
    
    for i, filename in enumerate(to_convert[214:]):
        print(f"   • {i+1}/{len(to_convert)}: {filename} → ", end="", flush=True)
        
        try:
            # PAUSE tous les 10 fichiers pour éviter quota
            if i > 0 and i % 10 == 0:
                print(f"\n   ⏸️  Pause 30 secondes pour quota...")
                time.sleep(30)
            
            # PAUSE plus longue tous les 50 fichiers
            if i > 0 and i % 50 == 0:
                print(f"\n   ⏸️  Pause 2 minutes pour quota...")
                time.sleep(120)
            
            # Télécharger CSV.gz
            remote_path = f"gdrive:movie_data_25m/chunks/{filename}"
            
            # Essayer avec timeout et retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = subprocess.run(
                        ["rclone", "cat", remote_path],
                        capture_output=True,
                        timeout=60
                    )
                    break
                except subprocess.TimeoutExpired:
                    if attempt < max_retries - 1:
                        print(f"⏱️  Timeout, tentative {attempt+2}/{max_retries}...")
                        time.sleep(10)
                    else:
                        raise
            
            # Vérifier si le fichier n'est pas vide
            if len(result.stdout) == 0:
                print("⚠️  Fichier vide ignoré")
                failed += 1
                continue
            
            # Décompresser et lire
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(result.stdout)) as gz:
                    df = pd.read_csv(gz)
            except Exception as e:
                print(f"❌ Erreur lecture: {e}")
                failed += 1
                continue
            
            # Vérifier si le DataFrame est vide
            if len(df) == 0:
                print("⚠️  DataFrame vide ignoré")
                failed += 1
                continue
            
            # Sauvegarder en Parquet
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False, compression='snappy')
            
            # Upload Parquet
            parquet_filename = filename.replace('.csv.gz', '.parquet')
            
            upload_success = False
            for attempt in range(3):
                try:
                    subprocess.run(
                        ["rclone", "rcat", f"gdrive:movie_data_25m/parquet/{parquet_filename}"],
                        input=parquet_buffer.getvalue(),
                        timeout=60
                    )
                    upload_success = True
                    break
                except:
                    print(f"⏱️  Upload timeout, tentative {attempt+2}/3...")
                    time.sleep(5)
            
            if upload_success:
                print(f"{parquet_filename} ✓")
                success += 1
            else:
                print("❌ Échec upload")
                failed += 1
            
            # Libérer mémoire
            del df, parquet_buffer, result
            
            # Pause courte entre chaque fichier
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)[:50]}")
            failed += 1
        
        # Garbage collection périodique
        if (i+1) % 5 == 0:
            gc.collect()
        
        # Progression
        if (i+1) % 25 == 0:
            elapsed = time.time() - start_time
            print(f"\n   📊 Progression: {i+1}/{len(to_convert)} fichiers en {elapsed/60:.1f} minutes")
            print(f"   ✅ Succès: {success} | ❌ Échecs: {failed}")
    
    total_time = time.time() - start_time
    
    print(f"\n" + "=" * 60)
    print("✅ CONVERSION TERMINÉE!")
    print("=" * 60)
    print(f"📊 RÉSULTATS:")
    print(f"   • Fichiers traités: {len(to_convert)}")
    print(f"   • Réussis: {success}")
    print(f"   • Échoués: {failed}")
    print(f"   • Temps total: {total_time/60:.1f} minutes")
    print(f"   • Dossier Parquet: gdrive:movie_data_25m/parquet/")
    print("=" * 60)

def continue_conversion():
    """Continue la conversion là où elle s'est arrêtée"""
    
    print("🔄 REPRISE DE LA CONVERSION")
    print("=" * 60)
    
    # Lister les fichiers Parquet existants
    result = subprocess.run(
        ["rclone", "lsf", "gdrive:movie_data_25m/parquet/"],
        capture_output=True,
        text=True
    )
    
    existing = [f.strip() for f in result.stdout.split('\n') if f.strip()]
    existing_names = [f.replace('.parquet', '') for f in existing]
    
    print(f"📊 Fichiers déjà convertis: {len(existing)}")
    
    # Lister les fichiers source
    result = subprocess.run(
        ["rclone", "lsf", "gdrive:movie_data_25m/chunks/"],
        capture_output=True,
        text=True
    )
    
    all_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
    
    # Filtrer les non convertis
    remaining = []
    for f in all_files:
        if f.replace('.csv.gz', '') not in existing_names:
            remaining.append(f)
    
    print(f"📊 Fichiers restants: {len(remaining)}")
    
    if remaining:
        print("\n🔧 Relancement de la conversion pour les fichiers restants...")
        time.sleep(3)
        
        # Relancer la conversion pour les fichiers restants
        convert_with_quota_subset(remaining)
    else:
        print("\n✅ TOUS LES FICHIERS SONT CONVERTIS!")

def convert_with_quota_subset(files_to_convert):
    """Convertit une liste spécifique de fichiers"""
    
    print(f"\n🔄 Conversion de {len(files_to_convert)} fichiers restants...")
    
    success = 0
    failed = 0
    
    for i, filename in enumerate(files_to_convert):
        print(f"   • {i+1}/{len(files_to_convert)}: {filename} → ", end="", flush=True)
        
        try:
            # Pause pour quota
            if i > 0 and i % 5 == 0:
                print(f"\n   ⏸️  Pause 20 secondes...")
                time.sleep(20)
            
            # Télécharger
            remote_path = f"gdrive:movie_data_25m/chunks/{filename}"
            result = subprocess.run(
                ["rclone", "cat", remote_path],
                capture_output=True,
                timeout=60
            )
            
            # Lire
            with gzip.GzipFile(fileobj=io.BytesIO(result.stdout)) as gz:
                df = pd.read_csv(gz)
            
            # Convertir et upload
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False)
            
            parquet_filename = filename.replace('.csv.gz', '.parquet')
            subprocess.run(
                ["rclone", "rcat", f"gdrive:movie_data_25m/parquet/{parquet_filename}"],
                input=parquet_buffer.getvalue(),
                timeout=60
            )
            
            print(f"{parquet_filename} ✓")
            success += 1
            
            del df, parquet_buffer
            
        except Exception as e:
            print(f"❌ Erreur: {str(e)[:50]}")
            failed += 1
        
        # Pause courte
        time.sleep(1)
    
    print(f"\n📊 Résultat partiel: {success} réussis, {failed} échoués")

if __name__ == "__main__":
    print("🎬 GESTIONNAIRE DE CONVERSION AVEC QUOTA")
    print("=" * 60)
    print("1. Lancer la conversion complète (avec pauses)")
    print("2. Continuer la conversion (reprendre)")
    print("3. Vérifier l'état")
    
    choice = input("\nVotre choix (1-3): ").strip()
    
    if choice == "1":
        convert_with_quota()
    elif choice == "2":
        continue_conversion()
    elif choice == "3":
        # Vérifier l'état
        result = subprocess.run(
            ["rclone", "lsf", "gdrive:movie_data_25m/parquet/"],
            capture_output=True,
            text=True
        )
        parquet_count = len([f for f in result.stdout.split('\n') if f])
        
        result = subprocess.run(
            ["rclone", "lsf", "gdrive:movie_data_25m/chunks/"],
            capture_output=True,
            text=True
        )
        csv_count = len([f for f in result.stdout.split('\n') if f])
        
        print(f"\n📊 ÉTAT ACTUEL:")
        print(f"   • Fichiers CSV.gz: {csv_count}")
        print(f"   • Fichiers Parquet: {parquet_count}")
        print(f"   • Progression: {parquet_count}/{csv_count} ({parquet_count/csv_count*100:.1f}%)")