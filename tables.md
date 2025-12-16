# Ports
    port_id (PK)
    name
    latitude
    longitude
    country
    capacity (optional)

# Warehouses
    warehouse_id (PK)
    name
    latitude
    longitude
    capacity (how much it can store)
    port_id (FK → Ports, if linked to a nearby port)

# Items
    item_id (PK)
    name
    category (e.g., electronics, food, raw materials)
    unit_price

# Warehouse_Inventory
    inventory_id (PK)
    warehouse_id (FK → Warehouses)
    item_id (FK → Items)
    quantity

# Shippings
    shipping_id (PK)
    from_port (FK → Ports),
    into_port (FK → Ports),
    inventory_id (FK → Warehouse_Inventory),

    arrived_at_port
    loaded_to_truck


# Infos and relations

## Ports
### Relations
    warehouse_id,
    warehouse_name
    warehouse_capacity
### Info
    port_id
    port_name
    country
    total_warehouse_count
    total_warehouse_capacity

## Warehouses
### Relations
    inventory_id  
    item_id  
    item_name  
    category  
    quantity  
    unit_price  
    total_value  
    is_shipping  

### Info
    warehouse_id  
    warehouse_name  
    connected_port  
    port_name  
    country  
    capacity  
    total_items  
    capacity_remaining  
    total_value  


## Items
### Relations
    warehouse_id  
    warehouse_name  
    quantity  
    total_value  

### Info
    item_id  
    name  
    category  
    unit_price  
    order_count  
    total_quantity  
    total_value  

## Inventory
### Relations
    warehouse_name
    item_name
    category
    quantity
    unit_price
    total_value            
    is_being_shipped       

### Info
    warehouse_name
    connected_port         
    item_name
    category
    quantity
    unit_price
    total_value
     

---

## Shippings
### Info
    item_id
    item_name
    quantity
    origin_port
    destination_port
    destination_warehouse
    arrived_at_port
    loaded_to_truck

