import * as Pinia from 'pinia';
import * as Vue from 'vue';

// The use prefix indicates that the function is a hook or a function that returns reactive state or functionality.
export const useUserStore = Pinia.defineStore('user', () => {

  const user = Vue.ref(null);

  const setUser = (newUser) => {
    user.value = newUser;
  }

  const clearUser = () => {
    user.value = null;
  }

  const isLoggedIn = Vue.computed(() => !!user.value) // !! converts a value to a boolean

  return { user, setUser, clearUser, isLoggedIn }
});