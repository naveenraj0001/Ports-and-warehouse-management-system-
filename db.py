import sqlite3 as sql

from pathlib import Path

DB_PATH = Path(__file__).parent / "database" / "pwms.db"


class Tables:
    PORTS = "Ports"
    WAREHOUSES = "Warehouses"
    ITEMS = "Items"
    INVENTORY = "WarehouseInventory"
    SHIPPINGS = "Shippings"

    @staticmethod
    def as_list():
        return [k for k in vars(Tables) if not k.startswith("__") and isinstance(getattr(Tables, k), str)]

    @staticmethod
    def get(key):
        return getattr(Tables, key)

    @staticmethod
    def rget(key):
        vals = Tables.as_list()
        for v in vals:
            if Tables.get(v) == key:
                return v
        return ""


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class DB:

    def __init__(self):
        if not DB_PATH.parent.is_dir():
            DB_PATH.parent.mkdir(parents=True)
        self.db = sql.connect(DB_PATH)
        self.db.row_factory = dict_factory
        self.db.execute("PRAGMA foreign_keys = ON;")

        self.cursor = self.db.cursor()

    def init_tables(self):
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {Tables.PORTS} (
                    port_id integer primary key AUTOINCREMENT,
                    name varchar(250),
                    latitude double,
                    longitude double,
                    country varchar(200),
                    capacity integer,
                    UNIQUE (latitude, longitude)
            );
        ''')

        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {Tables.WAREHOUSES} (
                    warehouse_id integer primary key AUTOINCREMENT,
                    name varchar(200),
                    latitude double,
                    longitude double,
                    capacity integer,
                    port_id integer,
                    FOREIGN KEY (port_id) REFERENCES Ports(port_id),
                    UNIQUE (latitude, longitude)
            );
        ''')

        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {Tables.ITEMS} (
                    item_id integer PRIMARY KEY AUTOINCREMENT,
                    name varchar(200),
                    category varchar(200),
                    unit_price double
            );
        ''')

        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {Tables.INVENTORY} (
                    inventory_id integer PRIMARY KEY AUTOINCREMENT,
                    warehouse_id integer,
                    item_id integer,
                    quantity integer,

                    FOREIGN KEY (item_id) REFERENCES Items(item_id),
                    FOREIGN KEY (warehouse_id)  REFERENCES Warehouses(warehouse_id)  
            );
        ''')
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {Tables.SHIPPINGS} (
                    shipping_id integer PRIMARY KEY AUTOINCREMENT,
                    from_port integer,
                    into_port integer,
                    inventory_id integer,

                    arrived_at_port boolean,
                    loaded_to_truck boolean,

                    FOREIGN KEY (from_port) REFERENCES Ports(port_id),
                    FOREIGN KEY (into_port)  REFERENCES Ports(port_id),
                    FOREIGN KEY (inventory_id)  REFERENCES WarehouseInventory(inventory_id)  
            );
        ''')
        self.db.commit()

    #
    # Select functions
    #
    def select(self, query: str, params: tuple = None) -> list[dict]:
        if params:
            rows = self.cursor.execute(query, params).fetchall()
            
        else:
            rows = self.cursor.execute(query).fetchall()
        
        if not rows and self.cursor.description:
            return [{col[0]: None for col in self.cursor.description}]
        return rows

    def get_column_names(self, table_name: str) -> list[str]:
        res = self.select(f'''SELECT * FROM {table_name}''')
        return list(res[0].keys())

    def get_table_data_all(self, table_name: str) -> list[dict]:
        return self.select(f'''SELECT * FROM {table_name}''')

    def get_port_data(self, port_id: int) -> dict:
        return self.select(f'''SELECT * FROM {Tables.PORTS} WHERE port_id = {port_id}''')[0]

    def get_warehouse_data(self, warehouse_id: int) -> dict:
        return self.select(f'''SELECT * FROM {Tables.WAREHOUSES} WHERE warehouse_id ={warehouse_id}''')[0]

    def get_shipping_locations(self, shipping_id: int) -> list[tuple[float, float]]:
        res = self.select(f"""
        SELECT 
        p1.latitude as "l1", p1.longitude as "l2", p2.latitude as "l3", p2.longitude as "l4" 
        FROM {Tables.SHIPPINGS} s
        JOIN {Tables.PORTS} p1 ON s.from_port = p1.port_id
        JOIN {Tables.PORTS} p2 ON s.into_port = p2.port_id
        WHERE shipping_id = {shipping_id}
        """)[0]

        return [(float(res["l1"]), float(res["l2"])), (float(res["l3"]), float(res["l4"]))]

    #
    # Insert functions
    #
    def insert_port_data(self, name: str, latitude: float, longitude: float,
                         country: str = "India", capacity: int = 1000):
        self.cursor.execute(f'''
            INSERT INTO {Tables.PORTS} (name, latitude, longitude, country, capacity) VALUES (?, ?, ?, ?, ?)
                            ''', (name, latitude, longitude, country, capacity))
        self.db.commit()

    def insert_warehouse_data(self, name: str, latitude: float, longitude: float,
                              capacity: int = 1000, port_id: int | None = None):
        self.cursor.execute(f'''
            INSERT INTO {Tables.WAREHOUSES} (name, latitude, longitude, capacity, port_id) VALUES (?, ?, ?, ?, ?)
                            ''', (name, latitude, longitude, capacity, port_id))
        self.db.commit()

    def insert_item_data(self, name: str, category: str | None, unit_price: float):
        self.cursor.execute(f'''
            INSERT INTO {Tables.ITEMS} (name, category, unit_price) VALUES (?, ?, ?)
                            ''', (name, category, unit_price))
        self.db.commit()

    def insert_inventory_data(self, warehouse_id: int, item_id: int, quantity: int):
        self.cursor.execute(f'''
            INSERT INTO {Tables.INVENTORY} (warehouse_id, item_id, quantity) VALUES(?, ?, ?)
                            ''', (warehouse_id, item_id, quantity))
        self.db.commit()

    def insert_shippings_data(self, from_port: int, into_port: int, inventory_id: int, arrived_at_port: bool, loaded_to_truck: bool):
        self.cursor.execute(f'''
            INSERT INTO {Tables.SHIPPINGS} (from_port, into_port, inventory_id, arrived_at_port, loaded_to_truck) VALUES(?, ?, ?, ?, ?)
                            ''', (from_port, into_port, inventory_id, arrived_at_port, loaded_to_truck))
        self.db.commit()

    #
    # Delete function
    #
    def delete_row(self, table_name: str, id: int):
        id_coloumn = self.get_column_names(table_name)[0]
        print("DELETING: ", table_name, id, id_coloumn)
        self.cursor.execute(
            f'''delete from {table_name} WHERE {id_coloumn} = {id}''')
        self.db.commit()

    #
    # Info functions
    #
    def get_port_relations(self, port_id: int) -> list[dict]:
        query = f"""
            SELECT 
                warehouse_id,
                name AS warehouse_name,
                capacity
            FROM {Tables.WAREHOUSES}
            WHERE port_id = ?;
        """
        return self.select(query,(port_id,))

    def get_port_info(self, port_id: int) -> list[dict]:
        query = f"""
            SELECT 
                p.port_id as "id",
                p.name AS port_name,
                p.country,
                COUNT(w.warehouse_id) AS total_warehouses,
                SUM(w.capacity) AS total_warehouse_capacity
            FROM {Tables.PORTS} p
            LEFT JOIN {Tables.WAREHOUSES} w ON p.port_id = w.port_id
            WHERE p.port_id = ?
            GROUP BY p.port_id;
        """
        return self.select(query,(port_id,))

    def get_warehouse_relations(self, warehouse_id: int) -> list[dict]:
        query = f"""
            SELECT
                i.inventory_id,
                it.item_id,
                it.name AS item_name,
                it.category,
                i.quantity,
                it.unit_price,
                (i.quantity * it.unit_price) AS total_value,
                i.inventory_id IN (SELECT inventory_id FROM {Tables.SHIPPINGS}) AS "is_shipping"
            FROM {Tables.INVENTORY} i
            INNER JOIN {Tables.ITEMS} it ON i.item_id = it.item_id
            WHERE i.warehouse_id = ?;
        """
        return self.select(query,(warehouse_id,))

    def get_warehouse_info(self, warehouse_id: int) -> list[dict]:
        query = f"""
            SELECT
                w.warehouse_id AS "id",
                w.name AS "warehouse_name",
                p.port_id as "connected_port",
                p.name AS port_name,
                p.country as "country",
                w.capacity as "capacity",
                IFNULL(SUM(i.quantity), 0) AS total_items,
                (w.capacity - IFNULL(SUM(i.quantity), 0)) AS capacity_remaining,
                IFNULL(SUM(i.quantity * it.unit_price), 0) AS total_value
            FROM {Tables.WAREHOUSES} w
            LEFT JOIN {Tables.PORTS} p ON w.port_id = p.port_id
            LEFT JOIN {Tables.INVENTORY} i ON w.warehouse_id = i.warehouse_id
            LEFT JOIN {Tables.ITEMS} it ON i.item_id = it.item_id
            WHERE w.warehouse_id = ?
            GROUP BY w.warehouse_id;
        """
        return self.select(query,(warehouse_id,))


    def get_item_relations(self, item_id: int) -> list[dict]:
        query = f"""
            SELECT
                inv.warehouse_id,
                w.name,
                inv.quantity,
                inv.quantity * i.unit_price as "total_value"
            FROM {Tables.ITEMS} i
            JOIN {Tables.INVENTORY} inv ON inv.item_id = i.item_id
            JOIN {Tables.WAREHOUSES} w ON w.warehouse_id = inv.warehouse_id
            WHERE i.item_id = ?
        """
        return self.select(query,(item_id,))

    def get_item_info(self, item_id: int) -> list[dict]:
        query = f"""
            SELECT
                i.item_id as "id",
                i.name,
                i.category,
                i.unit_price,
                COUNT(inv.quantity) as "order_count",
                SUM(inv.quantity) as "total_quantity",
                i.unit_price * inv.quantity as "total_value"
            FROM {Tables.ITEMS} i
            JOIN {Tables.INVENTORY} inv ON inv.item_id = i.item_id
            WHERE i.item_id = ?
            GROUP BY i.item_id;
        """
        return self.select(query,(item_id,))


    def get_inventory_relations(self, inventory_id: int) -> list[dict]:
        # TODO Implement
        query = f"""
            select
            w.name AS "warehouse_name",
            i.name AS "item_name",
            i.category,
            inv.quantity,
            i.unit_price,
            i.unit_price * inv.quantity as "total_value",
            inv.inventory_id IN (SELECT inventory_id FROM {Tables.SHIPPINGS}) AS "being_shipped"
            FROM {Tables.INVENTORY} inv
            JOIN {Tables.ITEMS} i ON i.item_id = inv.item_id
            JOIN {Tables.WAREHOUSES} w on w.warehouse_id = inv.warehouse_id
            where inv.inventory_id = ?
            GROUP BY inv.inventory_id;
        """
        return self.select(query,(inventory_id,))

    def get_inventory_info(self, inventory_id: int) -> list[dict]:
        # TODO Implement
        query = f"""
        SELECT
        w.name AS "warehouse_name",
        w.port_id AS "connected_port",
        p.name AS "port_name",
        i.name AS "item_name",
        i.category,
        inv.quantity,
        i.unit_price,
        inv.quantity * i.unit_price AS "total_value"
        FROM {Tables.INVENTORY} inv
        JOIN {Tables.WAREHOUSES} w ON w.warehouse_id = inv.warehouse_id
        JOIN {Tables.ITEMS} i ON i.item_id = inv.item_id
        JOIN {Tables.PORTS} p on p.port_id = w.port_id
        WHERE inv.inventory_id = ?;
        """
        return self.select(query,(inventory_id,))


    def get_shipping_info(self, shipping_id: int) -> list[dict]:
        # TODO Implement
        query = f"""
        SELECT
        i.item_id,
        i.name,
        inv.quantity,
        sh.from_port AS "origin_port",
        sh.into_port AS "destination_port",
        w.warehouse_id AS "destination_warehouse",
        sh.arrived_at_port,
        sh.loaded_to_truck
        FROM {Tables.SHIPPINGS} sh
        JOIN {Tables.INVENTORY} inv ON inv.inventory_id = sh.inventory_id
        JOIN {Tables.WAREHOUSES} w ON w.warehouse_id = inv.warehouse_id
        JOIN {Tables.ITEMS} i ON i.item_id = inv.item_id
        WHERE sh.shipping_id = ?;
        """
        return self.select(query,(shipping_id,))
