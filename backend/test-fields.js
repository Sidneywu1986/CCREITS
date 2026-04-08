const {db} = require('./database/db');

db.all(`
  SELECT 
    f.code, f.name, f.sector, f.sector_name,
    q.price, q.change_percent, q.volume, q.yield, q.market_cap
  FROM funds f
  LEFT JOIN quotes q ON f.code = q.fund_code
  WHERE q.id = (SELECT MAX(id) FROM quotes WHERE fund_code = f.code)
  LIMIT 1
`, [], (e, r) => {
  if (e) console.error(e);
  else {
    console.log('API返回的字段:');
    console.log(r[0]);
  }
  process.exit(0);
});
