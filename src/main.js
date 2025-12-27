// Library Imports
import { createPinia } from "pinia";
import { createApp } from "vue";

import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import { aliases, mdi } from "vuetify/iconsets/mdi";
import { VDateInput } from "vuetify/labs/VDateInput";
import { VFileUpload } from "vuetify/labs/VFileUpload";
import "@mdi/font/css/materialdesignicons.css";

// Internal Imports
import App from "@/App.vue";
import router from "@/router";

// Create application
const pinia = createPinia();
const app = createApp(App);
const vuetify = createVuetify({
  components: {
    ...components,
    VDateInput,
    VFileUpload,
  },
  directives,
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: "dark",
  },
});

app.use(pinia);
app.use(router);
app.use(vuetify);

app.mount("#app");

// This clears the console on hot reload
if (import.meta.hot) {
  import.meta.hot.on("vite:beforeUpdate", () => console.clear());
}
