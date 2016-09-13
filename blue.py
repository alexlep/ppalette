import sys
from core import models, main, database

database.init_db()

arg = ''.join(sys.argv[1:]) or True
if arg == 'i':
    with main.app.app_context():
    #drop_all_tables_and_sequences(db.engine)
        #print dir(models.Base)
        models.Base.metadata.drop_all()
        models.Base.metadata.create_all()

main.app.run(debug=True, host='0.0.0.0', threaded=True)
