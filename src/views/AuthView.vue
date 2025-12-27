<script setup>

import Pocketbase from 'pocketbase';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/UserStore';
import { userHelpers } from '@/composables/userHelpers';

const pb = new Pocketbase(import.meta.env.VITE_POCKETBASE_SERVER);
const username = ref('');
const password = ref('');
const router = useRouter();
const userStore = useUserStore();
const error = ref(null);

// Check the authData that is stored in localStorage - if the token has not expired, then you do not need to log in and can skip this page. 
if (pb.authStore.isValid) {
  userStore.setUser(pb.authStore.model)
  router.push('/');
}

async function registerClick() {
  await userHelpers().registerUser({ username, password, password }).then(() => {
    loginClick();
  });
}

async function loginClick() {

  try {
    const authData = await userHelpers().loginUser({ username, password });
    userStore.setUser(authData.record);
    router.push('/');
  } catch (error) {
    console.error('Error authenticating user: ', error)
  }
}

async function forgotPasswordClick() {
  pass
}

</script>

<template>
  <v-container class="fill-height">
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card>
          <v-form v-on:submit.prevent="loginClick">
            <v-text-field label="Username" v-model="username" required></v-text-field>
            <v-text-field label="Password" type="password" v-model="password" required></v-text-field>
            <v-card-actions>
              <v-btn v-on:click="loginClick" color="primary" type="submit">Login</v-btn>
              <v-btn v-on:click="registerClick" color="secondary">Register</v-btn>
              <v-btn v-on:click="forgotPasswordClick">Forgot Password</v-btn>
            </v-card-actions>
            <v-alert v-if="error" type="error" :text="error"></v-alert>
          </v-form>
        </v-card>
      </v-col>
    </v-row>
  </v-container>

</template>