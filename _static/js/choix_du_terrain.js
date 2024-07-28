function main() {
  var list1 = $("#conditions-primaires > ul")[0];
  list1.id = "features-list0";

  var list2 = $("#conditions-secondaires > ul")[0];
  list2.id = "features-list1";

  var list3 = $("#conditions-tertiaires > ul")[0];
  list3.id = "features-list2";

  var lists = [list1, list2, list3];

  // Generate IDs for lists entries
  for (var i = 0; i < lists.length; i++) {
    var list = lists[i];
    for (var j = 0; j < list.children.length; j++) {
      var child = list.children[j];
      child.id = list.id + j;
      child.innerHTML =
        '<i class="fa fa-bars list-grip"></i>' + child.innerHTML;
    }
  }

  for (var i = 0; i < lists.length; i++) {
    var list = lists[i];
    const itemOrder = localStorage.getItem(list.id);
    const itemOrderArr = itemOrder ? itemOrder.split(",") : [];

    Sortable.create(list, {
      group: "my_lists_group",
      handle: ".list-grip",
      dataIdAttr: "id",
      store: {
        set: function (sortable) {
          var order = sortable.toArray();
          localStorage.setItem(sortable.el.id, order);
        },
      },
      onSort: function (event) {
        var dest_list = event.to[Object.keys(event.to)[0]];
        var order = dest_list.toArray();
        localStorage.setItem(dest_list.el.id, order);
      },
    });

    let prevItem = null;
    itemOrderArr.forEach((item) => {
      const child = document.getElementById(item);
      if (prevItem === null) {
        list.insertBefore(child, list.firstChild);
      } else {
        const prevChild = document.getElementById(prevItem);
        prevChild.parentNode.insertBefore(child, prevChild.nextSibling);
      }
      prevItem = item;
    });
  }
}
document.addEventListener("DOMContentLoaded", main, false);
