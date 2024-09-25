from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configurazione del database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="pydb"
)

if db.is_connected():
    print("Connessione al database riuscita!")
else:
    print("Connessione al database fallita.")


def create_tables():
    cursor = db.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        category VARCHAR(255) NOT NULL,
        quantity INT NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        image_url VARCHAR(255)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INT AUTO_INCREMENT PRIMARY KEY,
        product_id INT NOT NULL,
        quantity INT NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)
    db.commit()


def check_and_add_columns():
    cursor = db.cursor()
    cursor.execute("DESCRIBE products")
    columns = [column[0] for column in cursor.fetchall()]

    if 'image_url' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN image_url VARCHAR(255)")
        db.commit()
        print("Colonna 'image_url' aggiunta alla tabella 'products'.")

    cursor.execute("DESCRIBE cart")
    columns = [column[0] for column in cursor.fetchall()]

    if 'quantity' not in columns:
        cursor.execute("ALTER TABLE cart ADD COLUMN quantity INT NOT NULL")
        db.commit()
        print("Colonna 'quantity' aggiunta alla tabella 'cart'.")


create_tables()
check_and_add_columns()


# Rotta per la homepage
@app.route('/')
def index():
    return render_template('index.html')


# Rotta per la gestione del negozio
@app.route('/manage')
def manage():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    return render_template('manage.html', products=products)


# Rotta per il lato cliente
@app.route('/shop')
def shop():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    return render_template('shop.html', products=products)


# Rotta per aggiungere un nuovo prodotto
@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    category = request.form['category']
    quantity = request.form['quantity']
    price = request.form['price']
    image_url = request.form['image_url']

    cursor = db.cursor()
    cursor.execute("INSERT INTO products (name, category, quantity, price, image_url) VALUES (%s, %s, %s, %s, %s)",
                   (name, category, quantity, price, image_url))
    db.commit()
    cursor.close()
    flash('Prodotto aggiunto con successo!')
    return redirect(url_for('manage'))


# Rotta per eliminare un prodotto
@app.route('/delete_product/<int:id>')
def delete_product(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    flash('Prodotto eliminato con successo!')
    return redirect(url_for('manage'))


# Rotta per aggiornare un prodotto
@app.route('/update_product/<int:id>', methods=['POST'])
def update_product(id):
    name = request.form['name']
    category = request.form['category']
    quantity = request.form['quantity']
    price = request.form['price']
    image_url = request.form['image_url']

    cursor = db.cursor()
    cursor.execute(
        "UPDATE products SET name = %s, category = %s, quantity = %s, price = %s, image_url = %s WHERE id = %s",
        (name, category, quantity, price, image_url, id))
    db.commit()
    cursor.close()
    flash('Prodotto aggiornato con successo!')
    return redirect(url_for('manage'))


# Rotta per il carrello
@app.route('/cart')
def cart():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
    SELECT cart.id, products.name, products.image_url, cart.quantity, products.price, (cart.quantity * products.price) AS total_price
    FROM cart
    JOIN products ON cart.product_id = products.id
    """)
    cart_items = cursor.fetchall()
    total_price = sum(item['total_price'] for item in cart_items)
    cursor.close()
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)


# Rotta per aggiungere un prodotto al carrello
@app.route('/add_to_cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    quantity = int(request.form['quantity'])
    cursor = db.cursor()
    cursor.execute("SELECT * FROM cart WHERE product_id = %s", (id,))
    cart_item = cursor.fetchone()
    cursor.fetchall()  # Leggi tutti i risultati per evitare l'errore "Unread result found"
    if cart_item:
        cursor.execute("UPDATE cart SET quantity = quantity + %s WHERE product_id = %s", (quantity, id))
    else:
        cursor.execute("INSERT INTO cart (product_id, quantity) VALUES (%s, %s)", (id, quantity))
    db.commit()
    cursor.close()
    flash('Prodotto aggiunto al carrello!')
    return redirect(url_for('shop'))


# Rotta per il pagamento
@app.route('/checkout')
def checkout():
    cursor = db.cursor()
    cursor.execute("DELETE FROM cart")
    db.commit()
    cursor.close()
    flash('Pagamento effettuato con successo!')
    return redirect(url_for('shop'))


# Rotta per scaricare il file CSV
@app.route('/download_csv')
def download_csv():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    df = pd.DataFrame(products)
    df.to_csv('products.csv', index=False)
    cursor.close()
    flash('File CSV scaricato con successo!')
    return redirect(url_for('manage'))


# Rotta per le statistiche
@app.route('/statistics')
def statistics():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    df = pd.DataFrame(products)

    # Statistiche di stoccaggio
    stock_stats = df.groupby('category')['quantity'].sum().reset_index()
    plt.figure(figsize=(10, 6))
    plt.bar(stock_stats['category'], stock_stats['quantity'], color='skyblue')
    plt.xlabel('Categoria')
    plt.ylabel('Quantità')
    plt.title('Quantità di Prodotti per Categoria')
    plt.savefig('static/stock_stats.png')
    plt.close()

    # Statistiche di vendita
    sales_stats = df.groupby('category')['price'].sum().reset_index()
    plt.figure(figsize=(10, 6))
    plt.bar(sales_stats['category'], sales_stats['price'], color='lightgreen')
    plt.xlabel('Categoria')
    plt.ylabel('Prezzo Totale')
    plt.title('Prezzo Totale dei Prodotti per Categoria')
    plt.savefig('static/sales_stats.png')
    plt.close()

    cursor.close()
    return render_template('statistics.html', stock_stats=stock_stats, sales_stats=sales_stats)


if __name__ == '__main__':
    app.run(debug=True)
