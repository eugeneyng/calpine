<script setup>
import { computed, reactive, ref, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import EditableText from "@/components/EditableText.vue";
import { unitHelpers } from "@/composables/unitHelpers";
import { useUnit } from "@/composables/useUnit";

const children = ref({});
const confirm = ref(false);
const confirmDialog = ref(false);
const confirmHeader = ref("");
const inventory = ref([]);
const inventoryDialog = ref(false);
const inventoryDialogData = reactive({
  name: null,
  unit: null,
});
const inventoryDialogItemId = ref(null);
const inventoryDialogMode = ref("create");
const occupantDialog = ref(false);
const occupantDialogData = ref({});
const occupants = ref({});
const occupantsArray = computed(() => {
  return Object.values(occupants.value).map(occupant => ({
    title: occupant.username, // v-autocomplete uses 'title' by default for display
    value: occupant.id,       // v-autocomplete uses 'value' for the actual value
    ...occupant              // Include all original properties
  }));
});
const parents = ref ({});
const route = useRoute();
const router = useRouter();
const snackbar = ref(false);
const snackbarText = ref("");
const tasks = ref([]);
const tasksDialog = ref(false);
const tasksDialogData = reactive({
  title: null,
  unit: null,
});
const tasksDialogItemId = ref(null);
const tasksDialogMode = ref("create");
const thingToDelete = ref("");
const thingToDeleteType = ref("");
const unit = useUnit();
const unitDialog = ref(false);
const unitDialogData = ref({});


const inventoryHeaders = [
  { title: "name", key: "name" },
  { title: "description", key: "description" },
  { title: "purchase_value", key: "purchase_value" },
  { title: "quantity", key: "quantity" },
  { title: "actions", key: "actions" },
];

const tasksHeaders = ref([
  { title: "title", key: "title" },
  { title: "description", key: "description" },
  { title: "owners", key: "owners" },
  { title: "updated", key: "updated" },
  { title: "due_date", key: "due_date" },
  { title: "actions", key: "actions" },
]);

onMounted(async () => {
  await unit.fetchUnit(route.params.id);
  children.value = await unit.fetchChildren();
  inventory.value = await unit.fetchItems();
  occupants.value = await unit.fetchOccupants();
  console.log(occupantsArray);
  parents.value = await unit.fetchParents();
  tasks.value = await unit.fetchTasks();
});

async function confirmDelete(action) {
  if (action == "item") {
    unit.deleteItem(thingToDelete.value).then(async () => {
      inventory.value = await unit.fetchItems();
    })
    snackbarText.value = "Item " + thingToDelete.value + " deleted";
    snackbar.value = true;
  } else if (action == "task") {
    unit.deleteTask(thingToDelete.value).then(async () => {
      tasks.value = await unit.fetchTasks();
    });
    snackbarText.value = "Task " + thingToDelete.value + " deleted";
    snackbar.value = true;
  }
    confirmDialog.value = false;
    confirmHeader.value = "";
}

async function inventoryDialogOpen(itemId, action) {
  inventoryDialogMode.value = action;
  inventoryDialogItemId.value = itemId;

  if (action == "create") {
    Object.keys(inventoryDialogData).forEach(key => inventoryDialogData[key] = null);
    console.log("Creating item");
    inventoryDialog.value = true;
  } else if (action == "edit") {
    console.log("Editing " + itemId);
    Object.assign(inventoryDialogData, await unit.fetchItem(itemId));
    inventoryDialog.value = true;
  } else if (action == "delete") {
    thingToDelete.value = itemId;
    thingToDeleteType.value = "item";
    console.log("Deleting " + itemId);
    confirmHeader.value = "Are you sure you want to delete itemId " + itemId + "?";
    confirmDialog.value = true;
  } 

}

async function inventoryDialogClose(itemId, action) {

  if (action == "create") {
    inventoryDialogData.unit = route.params.id
    unit.createItem(inventoryDialogData).then(async () => {
      inventory.value = await unit.fetchItems();
    });
    snackbarText.value = "Item " + inventoryDialogData.name + " created";
    snackbar.value = true;
  } else if (action == "edit") {
    console.log(inventoryDialogData);
    unit.updateItem(inventoryDialogData).then(async () => {
      inventory.value = await unit.fetchItems();
    })
    snackbarText.value = "Item " + inventoryDialogData.name + " updated";
    snackbar.value = true;
  } 

  inventoryDialog.value = false;
}

async function tasksDialogOpen(itemId, action) {
  tasksDialogMode.value = action;
  tasksDialogItemId.value = itemId;

  if (action == "create") {
    Object.keys(tasksDialogData).forEach(key => tasksDialogData[key] = null);
    console.log("Creating item");
    tasksDialog.value = true;
  } else if (action == "edit") {
    console.log("Editing " + itemId);
    Object.assign(tasksDialogData, await unit.fetchTask(itemId));
    tasksDialog.value = true;
  } else if (action == "delete") {
    thingToDelete.value = itemId;
    thingToDeleteType.value = "task";
    console.log("Deleting " + itemId);
    confirmHeader.value = "Are you sure you want to delete itemId " + itemId + "?";
    confirmDialog.value = true;
  } 
}

async function tasksDialogClose(itemId, action) {
  if (action == "create") {
    tasksDialogData.unit = route.params.id
    unit.createTask(tasksDialogData).then(async () => {
      tasks.value = await unit.fetchTasks();
    });
    snackbarText.value = "Task " + tasksDialogData.name + " created";
    snackbar.value = true;
  } else if (action == "edit") {
    console.log(tasksDialogData);
    unit.updateTask(tasksDialogData).then(async () => {
      tasks.value = await unit.fetchTasks();
    })
    snackbarText.value = "Task " + tasksDialogData.name + " updated";
    snackbar.value = true;
  } 

  tasksDialog.value = false;

}

function navigateToUnit(id) {
  router.push({
    name: "unit", params: {
      id: id
    }
  })
}

function navigateToUser(id) {
  console.log(id);
}

</script>

<template>

  <v-overlay v-if="unit.loading.value" v-model="unit.loading.value" class="align-center justify-center">
    <v-progress-circular indeterminate></v-progress-circular>
  </v-overlay>

  <v-container v-if="!unit.loading.value">

    <v-row>

      <v-col cols="auto">
        <v-breadcrumbs density="compact" divider="/">
          <v-breadcrumbs-item 
            v-for="(parent, id) in parents" 
            v-bind:key="id" 
            v-on:click="navigateToUnit(parent.id)">
            <template v-if="parent">
              <v-hover v-slot="{ isHovering, props }">
                <v-card v-bind="props" v-bind:color="isHovering ? 'primary' : 'transparent'">{{ parent.name }}</v-card>
              </v-hover>
            </template>
          </v-breadcrumbs-item>
          /
          <v-breadcrumbs-item>
            <v-hover v-slot="{ isHovering, props }">
              <editable-text 
                v-bind="props" 
                v-bind:color="isHovering ? 'secondary' : 'transparent'"
                v-model="unit.data.value.name" 
                v-on:blur="unit.updateUnit()"
                v-on:click:append-inner="unit.updateUnit()" 
                v-on:keyup.enter="unit.updateUnit()">
              </editable-text>
            </v-hover>
          </v-breadcrumbs-item>
          <v-breadcrumbs-item>
            <v-icon icon="mdi-menu-down" id="children-activator" />
            <v-menu activator="#children-activator">
              <v-list>
                <v-list-item v-for="(child, id) in children" :key="id" v-on:click="navigateToUnit(child.id)">
                  {{ child.name }}
                </v-list-item>
                <v-list-item v-on:click="createUnit">
                  +
                </v-list-item>
              </v-list>
            </v-menu>
          </v-breadcrumbs-item>
        </v-breadcrumbs>
      </v-col>

    </v-row>

    <v-row class="mt-0 align-center" cols="auto">

      <v-col cols="auto">
        <v-avatar 
          v-for="(occupant, id) in occupants" :key="id" 
          v-on:click="navigateToUser(occupant.id)" 
          class="mr-n4" 
          color="surface-variant"
          variant="elevated">
          <span class="text-h6"> {{ occupant.username.charAt(0).toUpperCase() }} </span>
        </v-avatar>
        <v-avatar v-on:click="editOccupants()" class="text-h6" color="surface-variant" variant="elevated"> + </v-avatar>
      </v-col>

      <v-col cols="auto">
        <v-chip v-if="unit.data.value.bedrooms || unit.data.value.bathrooms || unit.data.value.square_footage">
          {{ unit.data.value.bedrooms ? unit.data.value.bedrooms + " beds" : "" }} | 
          {{ unit.data.value.bathrooms ? unit.data.value.bathrooms + " baths" : "" }} | 
          {{ unit.data.value.square_footage ? unit.data.value.square_footage + " sqft" : "" }}
        </v-chip>
      </v-col>

    </v-row>

    <v-row class="mt-0">
      <v-col cols="auto">
        <v-hover v-slot="{ isHovering, props }">
          <editable-text
            v-bind="props" 
            v-bind:color="isHovering ? 'secondary' : 'transparent'" 
            v-model="unit.data.value.description" 
            v-on:blur="unit.updateUnit()"
            v-on:click:append-inner="unit.updateUnit()" 
            v-on:keyup.enter="unit.updateUnit()">
          </editable-text>
        </v-hover>
        
      </v-col>
    </v-row>

    <v-row>

      <v-col cols="auto">
        <v-data-table
          v-bind:items="tasks"
          v-bind:headers="tasksHeaders"
          hide-default-footer>
          <template v-slot:top>
            <v-toolbar>
              <v-toolbar-title>Tasks</v-toolbar-title>
              <v-btn v-on:click="tasksDialogOpen(null, 'create')" prepend-icon="mdi-plus" >Add A Task</v-btn>
            </v-toolbar>
          </template>
          <template v-slot:item.actions="{ item }">
            <div>
              <v-icon icon="mdi-pencil" v-on:click="tasksDialogOpen(item.id, 'edit')"></v-icon>
              <v-icon icon="mdi-delete" v-on:click="tasksDialogOpen(item.id, 'delete')"></v-icon>
            </div>
          </template>
        </v-data-table>
      </v-col>
      
      <v-col cols="auto">
        <v-data-table
          v-bind:items="inventory"
          v-bind:headers="inventoryHeaders"
          hide-default-footer>
          <template v-slot:top>
            <v-toolbar>
              <v-toolbar-title>Inventory</v-toolbar-title>
              <v-btn v-on:click="inventoryDialogOpen(null, 'create')" prepend-icon="mdi-plus">Add An Item</v-btn>
            </v-toolbar>
          </template>
          <template v-slot:item.actions="{ item }">
            <div>
              <v-icon icon="mdi-pencil" v-on:click="inventoryDialogOpen(item.id, 'edit')"></v-icon>
              <v-icon icon="mdi-delete" v-on:click="inventoryDialogOpen(item.id, 'delete')"></v-icon>
            </div>
          </template>
        </v-data-table>
      </v-col>

    </v-row>

  </v-container>

  <v-container>
    <v-dialog v-model="confirmDialog">
      <v-card>
        <v-card-title>{{ confirmHeader }}</v-card-title>
        <v-card-actions>
          <v-btn v-on:click="confirmDialog = false">Cancel</v-btn>
          <v-btn v-on:click="confirmDelete(thingToDeleteType)">Confirm</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>

  <v-container>
    <v-dialog v-model="inventoryDialog">
    <!--v-model is the same as v-bind: and v-on:input together-->
      <v-card>
        <v-card-title>{{ inventoryDialogMode === "create" ? "New Item" : "Edit Item" }}</v-card-title>
        <v-form v-on:submit.prevent="inventoryDialogClose(inventoryDialogItemId, inventoryDialogMode)">
          <v-text-field
            v-model="inventoryDialogData.name"
            label="Item Name"
            required
          ></v-text-field>
          <v-text-field
            v-model="inventoryDialogData.description"
            label="Item Description"
          ></v-text-field>
          <v-date-input
            v-model="inventoryDialogData.purchase_date" 
            label="Purchase Date">
          </v-date-input>
          <v-number-input 
            controlVariant="split"
            v-model="inventoryDialogData.purchase_value" 
            label="Purchase Price">
          </v-number-input>
          <v-number-input 
            controlVariant="split"
            v-model="inventoryDialogData.quantity" 
            label="Quantity">
          </v-number-input>
          <v-file-upload 
            clearable
            multiple
            density="compact" 
            variant="compact"
            v-model="inventoryDialogData.documents"
            label="Item Description"
          ></v-file-upload>
          <v-card-actions>
            <v-btn color="primary" type="submit">{{ inventoryDialogMode === 'create' ? 'Create' : 'Update' }}</v-btn>
            <v-btn v-on:click="inventoryDialog = false">Close</v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
    </v-dialog>
  </v-container>

  <v-container>
    <v-dialog v-model="occupantDialog"></v-dialog>
  </v-container>

  <v-container>
    <v-dialog v-model="tasksDialog">
    <!--v-model is the same as v-bind: and v-on:input together-->
      <v-card>
        <v-card-title>{{ tasksDialogMode === "create" ? "New Task" : "Edit Task" }}</v-card-title>
        <v-form v-on:submit.prevent="tasksDialogClose(tasksDialogItemId, tasksDialogMode)">
          <v-text-field
            v-model="tasksDialogData.title"
            label="Task Title"
            required
          ></v-text-field>
          <v-text-field
            v-model="tasksDialogData.description"
            label="Task Description"
          ></v-text-field>
          <v-autocomplete
            v-model="tasksDialogData.owners"
            label="Owners"
            multiple
            chips
            clearable
            :items=occupantsArray
          ></v-autocomplete>
          <v-date-input
            v-model="tasksDialogData.due_date" 
            label="Due Date"> 
          </v-date-input>
          <v-date-input
            v-model="tasksDialogData.updated"
            label="Updated"
            disabled>
          </v-date-input>
          <v-card-actions>
            <v-btn color="primary" type="submit">{{ tasksDialogMode === 'create' ? 'Create' : 'Update' }}</v-btn>
            <v-btn v-on:click="tasksDialog = false">Close</v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
    </v-dialog>
  </v-container>

  <v-container>
    <v-dialog v-model="unitDialog"></v-dialog>
  </v-container>
  
  <v-snackbar v-model="snackbar">{{ snackbarText }}</v-snackbar>
</template>
