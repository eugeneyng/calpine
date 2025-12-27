<script setup>
import { reactive, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { unitHelpers } from "@/composables/unitHelpers";
import { useUserStore } from "@/stores/UserStore";

const dialog = ref(false);
const dialogData = reactive({
  name: "",
  description: "",
  owner: useUserStore().user.id,
});
const router = useRouter();
const units = ref([]);

onMounted(async () => {
  units.value = await unitHelpers().getHomeUnits(useUserStore().user.id);
});

function submitNewUnit() {
  // Create new unit
  unitHelpers().createUnit(dialogData);

  //Reset the dialog
  dialog.value = false;
  dialogData.value = {
    name: "",
    description: "",
    owner: useUserStore().user.id,
  };
}

function navigateToUnit(id) {
  router.push({
    name: "unit",
    params: {
      id: id,
    },
  });
}
</script>

<template>
  <v-container>
    <v-row align="center" justify="center">
      <!-- Each column is 3-wide at all screen sizes except for xs screens, where it is 1-wide -->
      <v-col
        cols="12"
        xs="1"
        sm="3"
        md="3"
        lg="3"
        v-for="unit in units"
        :key="unit.id"
      >
        <v-card
          v-on:click="navigateToUnit(unit.id)"
          align="center"
          height="8vh"
          justify="center"
          class="text-truncate"
        >
          <v-card-title>{{ unit.name }}</v-card-title>
          <v-card-text>{{ unit.description }}</v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" xs="1" sm="3" md="3" lg="3">
        <v-card
          align="center"
          height="8vh"
          justify="center"
          v-on:click="dialog = true"
        >
          <v-card-title>+</v-card-title>
          <v-card-text>Add new unit</v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
  <v-container>
    <v-dialog max-width="80vw" v-model="dialog">
      <v-card>
        <v-card-title>New Unit</v-card-title>
        <v-form v-on:submit.prevent="submitNewUnit">
          <!--v-model is the same as v-bind: and v-on:input together-->
          <v-text-field
            v-model="dialogData.name"
            label="Unit Name"
            required
          ></v-text-field>
          <v-text-field
            v-model="dialogData.description"
            label="Unit Description"
          ></v-text-field>
          <v-card-actions>
            <v-btn color="primary" type="submit">Submit</v-btn>
            <v-btn v-on:click="dialog = false">Close</v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
    </v-dialog>
  </v-container>
</template>
