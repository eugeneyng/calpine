<script setup>

import { ref } from 'vue';

import Pocketbase from 'pocketbase';
import { useUserStore } from '@/stores/UserStore'
import { useTheme } from 'vuetify'

const pb = new Pocketbase(import.meta.env.VITE_POCKETBASE_SERVER);
const userStore = useUserStore();
const theme = useTheme();

const drawer = ref(false);

function toggleTheme() {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark';
}

function logOutClick() {
  pb.authStore.clear();
  userStore.clearUser();
}

</script>

<template>
  <v-app-bar>
    <v-app-bar-nav-icon v-on:click="drawer = !drawer"></v-app-bar-nav-icon>
    <v-app-bar-title>
      <router-link to="/" class="text-decoration-none">HOMA</router-link>
    </v-app-bar-title>

    <v-btn icon>
      <v-icon>mdi-account</v-icon>
      <v-menu activator="parent">
        <v-list v-if="pb.authStore.isValid">
          <v-list-item to="/settings"> <!-- v-list-item has built in router-link functionality ! -->
            <v-list-item-title>{{ userStore.user?.username }}</v-list-item-title>
          </v-list-item>
          <v-list-item to="/login" v-on:click="logOutClick">
            <v-list-item-title>Log Out</v-list-item-title>
          </v-list-item>
        </v-list>
        <v-list v-else>
          <v-list-item to="/login">
            <v-list-item-title>Log In</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-btn>


    <v-btn icon v-on:click="toggleTheme">
      <v-icon>mdi-theme-light-dark</v-icon>
    </v-btn>
  </v-app-bar>

  <v-navigation-drawer v-model="drawer">
    <v-list>
      <v-list-item to="/">
        <v-list-item-title>Units</v-list-item-title>
      </v-list-item>
      <v-list-item to="/inventory">
        <v-list-item-title>Inventory</v-list-item-title>
      </v-list-item>
      <v-list-item to="/tasks">
        <v-list-item-title>Tasks</v-list-item-title>
      </v-list-item>
      <v-list-item to="/people">
        <v-list-item-title>People</v-list-item-title>
      </v-list-item>
      <v-list-item to="/settings">
        <v-list-item-title>Settings</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>