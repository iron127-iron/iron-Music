with open('web_panel/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 98 (index 97) - escape function
# The single quote should be escaped as ' (HTML entity) or just use a backslash escape
lines[97] = "function escape(s){return(s||'').replace(/[&<>\"']/g,c=>({'&':'&','<':'<','>':'>','\"':'\"',\"'\":\"'\"}[c]))}\n"

with open('web_panel/index.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed')