# verification_fixed.py
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text

def verify_tables_correct():
    """Vérification CORRECTE des tables"""
    
    print("🔍 VÉRIFICATION CORRECTE DES TABLES")
    print("=" * 50)
    
    # Connexion
    engine = create_engine('postgresql://admin:admin123@localhost:5432/d')
    
    # 1. Voir les tables EXACTEMENT telles qu'elles sont
    print("📋 Tables EXACTES (avec casse):")
    
    query = text("""
    SELECT 
        table_name,
        (SELECT COUNT(*) FROM information_schema.columns 
         WHERE table_schema = 'public' 
         AND table_name = t.table_name) as columns_count
    FROM information_schema.tables t
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """)
    
    with engine.connect() as conn:
        tables_df = pd.read_sql(query, conn)
        print(tables_df.to_string())
    
    # 2. Vérifier avec les noms EXACTS
    print("\n🎯 Test avec les noms EXACTS:")
    
    exact_table_names = list(tables_df['table_name'])
    
    for table in exact_table_names:
        try:
            query = text(f'SELECT COUNT(*) as count FROM "{table}"')
            with engine.connect() as conn:
                count = pd.read_sql(query, conn).iloc[0,0]
            print(f"   ✅ {table}: {count:,} lignes")
        except Exception as e:
            print(f"   ❌ {table}: Erreur - {str(e)[:50]}...")
    
    # 3. Test sans guillemets (si tables en minuscules)
    print("\n🔤 Test sans guillemets (si lowercase):")
    
    for table in exact_table_names:
        try:
            # Essayer sans guillemets
            query = text(f'SELECT COUNT(*) as count FROM {table}')
            with engine.connect() as conn:
                count = pd.read_sql(query, conn).iloc[0,0]
            print(f"   ✅ {table} (sans guillemets): {count:,} lignes")
        except Exception as e:
            print(f"   ❌ {table} (sans guillemets): Erreur")
    
    engine.dispose()
    
    print("\n" + "=" * 50)
    print("💡 RECOMMANDATION:")
    print("Utilisez les noms EXACTS ci-dessus dans votre script d'export")
    print("=" * 50)
    
    return exact_table_names

def test_export_with_correct_names():
    """Test avec les bons noms de tables"""
    
    print("\n🧪 TEST D'EXPORT AVEC NOMS CORRIGÉS")
    print("=" * 50)
    
    engine = create_engine('postgresql://admin:admin123@localhost:5432/movierec')
    
    # Basé sur votre sortie, les tables sont probablement :
    tables_to_test = ['dim_movies', 'dim_users', 'fact_ratings']
    
    for table in tables_to_test:
        try:
            # Essayer les deux formats
            for query_format in [
                f'SELECT COUNT(*) FROM "{table}"',  # Avec guillemets
                f'SELECT COUNT(*) FROM {table}',     # Sans guillemets
                f'SELECT COUNT(*) FROM {table.lower()}',  # En minuscules
                f'SELECT COUNT(*) FROM {table.upper()}'   # En majuscules
            ]:
                try:
                    count = pd.read_sql(query_format, engine).iloc[0,0]
                    print(f"✅ {query_format}: {count:,} lignes")
                    break
                except:
                    continue
        except Exception as e:
            print(f"❌ {table}: Aucun format ne fonctionne")
    
    engine.dispose()

if __name__ == "__main__":
    # 1. Vérifier les noms exacts
    table_names = verify_tables_correct()
    
    # 2. Tester l'export
    test_export_with_correct_names()
    
    # 3. Donner la solution
    print("\n🎯 SOLUTION POUR VOTRE SCRIPT:")
    print("=" * 50)
    
    if 'dim_movies' in table_names:
        print("✅ Utilisez DANS VOTRE SCRIPT :")
        print("""
# Ligne ~13 (films):
movies = pd.read_sql("SELECT * FROM dim_movies", engine)

# Ligne ~17 (utilisateurs):
users = pd.read_sql("SELECT * FROM dim_users", engine)

# Ligne ~35 (notes):
table_name = "fact_ratings"  # ← EXACTEMENT comme dans la liste
""")
    else:
        print("❓ Les tables semblent avoir une casse différente")
        print("Essayez avec des guillemets:")
        print("""
movies = pd.read_sql('SELECT * FROM "dim_movies"', engine)
""")