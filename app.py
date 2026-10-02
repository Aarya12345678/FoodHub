from flask import Flask,render_template,redirect,request,url_for,session
import pandas as pd
import numpy as np
import os
from datetime import datetime
app=Flask(__name__)
app.secret_key="restaurant_secret_key"
MENU_FILE="menu.csv"
ORDERS_FILE="orders.csv"
INVENTORY_FILE="inventory.csv"
def initialize_files():
    if not os.path.exists(MENU_FILE):
        menu=pd.DataFrame({
            "item_id":[101,102,103,104,105,106],
            "item":[
                "BURGER",
                "PIZZA",
                "FRENCH FRIES",
                "PASTA",
                "MOJITO",
                "ICE CREAM"
            ],
            "category":[
                "MAIN COURSE",
                "MAIN COURSE",
                "STARTER",
                "MAIN COURSE",
                "BEVERAGE",
                "DESSERT"
            ],
            "price":[120,250,80,180,50,90]

        })
        menu.to_csv(MENU_FILE,index=False)
        if not os.path.exists(ORDERS_FILE):
            orders=pd.DataFrame( 
            columns=[
                "order_id",
                "date",
                "item_id",
                "item",
                "quantity",
                "price",
                "total"
            ]
            )
            orders.to_csv(ORDERS_FILE,index=False)
        if not os.path.exists(INVENTORY_FILE):
            inventory=pd.DataFrame({
                "item_id":[101,102,103,104,105,106],
                "stock":[50,30,60,40,100,40]

            })
            inventory.to_csv(INVENTORY_FILE,index=False)
initialize_files()
@app.route("/")
def index():
    menu=pd.read_csv(MENU_FILE)
    inventory=pd.read_csv(INVENTORY_FILE)
    total_items=len(menu)
    low_stock=len(inventory[inventory["stock"]<=5])
    if os.path.exists(ORDERS_FILE):
        orders=pd.read_csv(ORDERS_FILE)
        if len(orders)>0:
            total_revenue=orders["total"].sum()
            total_orders=orders["order_id"].nunique()
        else:
            total_revenue=0
            total_orders=0
        return render_template(
            "index.html",
            total_items=total_items,
            low_stock=low_stock,
            total_revenue=total_revenue,
            total_orders=total_orders
        )
@app.route("/menu")
def menu():
    menu_data=pd.read_csv(MENU_FILE)
    inventory=pd.read_csv(INVENTORY_FILE)
    data=menu_data.merge(inventory,on="item_id")
    return render_template(
        "menu.html",
        menu=data.to_dict("records")
    )
@app.route("/cart")
def cart():
    cart=session.get("cart",[])
    subtotal=0
    for item in cart:
        item["total"]=(
            item["price"]*item["quantity"]
        )
        subtotal+=item["total"]
    tax=subtotal*0.05
    total=subtotal+tax
    return render_template(
        "cart.html",
        cart=cart,
        subtotal=subtotal,
        tax=tax,
        total=total
    )
@app.route("/add_to_cart/<int:item_id>",methods=["POST"])
def add_to_cart(item_id):
    quantity=int(request.form["quantity"])
    menu=pd.read_csv(MENU_FILE)
    inventory=pd.read_csv(INVENTORY_FILE)
    item=menu[menu["item_id"]==item_id]
    if item.empty:
        return redirect(url_for("menu"))
    stock=inventory[
        inventory["item_id"]==item_id]["stock"].iloc[0]
    if quantity > stock:
        return redirect(url_for("menu"))
    cart=session.get("cart",[])
    found=False
    for cart_item in cart:
        if cart_item["item_id"]== item_id:
            cart_item["quantity"]+=quantity
            found=True
    if not found:
        cart.append({
            "item_id":int(item_id),
            "item":item.iloc[0]["item"],
            "price":float(item.iloc[0]["price"]),
            "quantity":quantity
        }) 
    session["cart"]=cart
    return redirect(url_for("cart"))
@app.route("/remove/<int:item_id>")
def remove_item(item_id):
    cart=session.get("cart",[])
    cart=[
        item for item in cart 
        if item["item_id"]!=item_id

    ]
    session["cart"]=cart
    return redirect(url_for("cart"))
@app.route("/place_order",methods=["POST"])
def place_order():
    cart=session.get("cart",[])
    if not cart:
        return redirect(url_for("menu"))
    orders=pd.read_csv(ORDERS_FILE)
    inventory=pd.read_csv(INVENTORY_FILE)
    if len(orders)==0:
        order_id=1001
    else:
        order_id=int(
            orders["order_id"].max()
        )+1
    date=datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    new_orders=[]
    subtotal=0
    for item in cart:
            item_total=(
                item["price"]*item["quantity"]
            )
            subtotal+=item_total
            new_orders.append({
                "order_id":order_id,
                "date":date,
                "item_id":item["item_id"],
                "item":item["item"],
                "quantity":item["quantity"],
                "price":item["price"],
                "total":item_total
            })
            inventory.loc[
                inventory["item_id"]==item["item_id"],
                "stock"
            ]-= item["quantity"]
    new_orders_df=pd.DataFrame(new_orders)
    orders=pd.concat(
            [orders,new_orders_df],
            ignore_index=True
        )
    orders.to_csv(
                ORDERS_FILE,
                index=False
            )
    inventory.to_csv(
            INVENTORY_FILE,
            index=False
            )
    tax=subtotal*0.05
    grand_total=subtotal+tax
    session["cart"]=[]
    return render_template(
            "bill.html",
            order_id=order_id,
            date=date,
            items=new_orders,
            subtotal=subtotal,
            tax=tax,
            total=grand_total
            )
@app.route("/sales")
def sales():
    orders=pd.read_csv(ORDERS_FILE)
    if orders.empty:
        return render_template(
            "sales.html",
            total_orders=0,
            revenue=0,
            average_order=0,
            best_item="No Sales yet",
            item_sales=[],
            category_sales=[]
        )
    total_orders=orders["order_id"].nunique()
    revenue=orders["total"].sum()
    average_order=(
        revenue/total_orders
    )
    item_sales=(
        orders
        .groupby("item")["quantity"]
        .sum()
        .sort_values(
            ascending=False
        )
    )
    best_item=item_sales.index[0]
    item_sales_table=(
        orders
        .groupby("item")
        .agg(
            quantity=("quantity","sum"),
            revenue=("total","sum")
        )
        .reset_index()
        .sort_values(
            "revenue",
            ascending=False
        )
    )
    menu=pd.read_csv(MENU_FILE)
    merged=orders.merge(
        menu[["item_id","category"]],
        on="item_id",
        how="left"
    )
    category_sales=(
        merged
        .groupby("category")["total"]
        .sum()
        .reset_index()

    )
    return render_template(
        "sales.html",
        total_orders=total_orders,
        revenue=revenue,
        average_order=average_order,
        best_item=best_item,
        item_sales=item_sales_table.to_dict("records"),
        category_sales=category_sales.to_dict("records")
    )
if __name__=="__main__":
    app.run(debug=True)