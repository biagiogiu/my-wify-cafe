let current_wifi_rating = parseInt({{wifi|int}});
console.log(current_wifi_rating);
let current_coffee_rating = parseInt({{coffee|int}});
console.log(current_coffee_rating);
let current_power_rating = parseInt({{power|int}});
console.log(current_power_rating);

let wifi_ID = "wifi" + (5 - current_wifi_rating);
let coffee_ID = "coffee" + (5 - current_coffee_rating);
let power_ID = "power" + (5 - current_power_rating);

document.getElementById(wifi_ID).checked = true;
document.getElementById(coffee_ID).checked = true;
document.getElementById(power_ID).checked = true;
