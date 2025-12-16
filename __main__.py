from pwms import PWSM, DB

def main():
    database = DB()
    database.init_tables()
    
    mapview = PWSM(database)
    mapview.mainloop()

if __name__ == "__main__":
    main()
