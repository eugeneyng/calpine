import { reactive, ref, onMounted } from "vue";
import Pocketbase from "pocketbase";

// This is intended to be a helper utility for handling users in general

export function userHelpers() {
    
  const pb = new Pocketbase(import.meta.env.VITE_POCKETBASE_SERVER);

  async function loginUser({ username, password }) {

    try {
        const authData = await pb.collection('users').authWithPassword(username.value, password.value);
        return authData;
    } catch (error) {
        console.error('Error authenticating user: ', error)
    }

  }

  async function registerUser({ username, password, passwordConfirm, ...args }) {

    try {
        const user = await pb.collection('users').create({
          username: username.value,
          password: password.value,
          passwordConfirm: password.value
        })
        console.log('User registered successfully: ', user)
      } catch (error) {
        console.error('Error registering user: ', error)
      }
  }

  return {
    loginUser,
    registerUser,
  };
}