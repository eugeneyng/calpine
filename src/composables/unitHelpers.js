import { reactive, ref, onMounted } from "vue";
import Pocketbase from "pocketbase";

// This is intended to be a helper utility for handling units in general

export function unitHelpers() {
  const pb = new Pocketbase(import.meta.env.VITE_POCKETBASE_SERVER);

  async function createItem({ unit, ...args}) {
    try {
      const record = await pb.collection("items").create({
        unit: unit,
        ...args
      });
      console.log("Item created: ", record);
    } catch (error) {
      console.error("Error creating record: ", error);
    }
  }

  async function createUnit({ name, owner, ...args }) {
    try {
      const record = await pb.collection("units").create({
        name: name,
        owner: owner,
        ...args
      });
      console.log("Unit created: ", record);
    } catch (error) {
      console.error("Error creating record: ", error);
    }
  }

  async function getHomeUnits(owner) {
    try {

      // Create a promise that rejects after a timeout
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Request timed out')), 10000); // 10 seconds timeout
      });
      const filter = `owner = "${owner}" && (parent = "" || parent = null)`;
      const getHomesPromise = pb.collection('units').getFullList({
          filter: filter,
          sort: '-created',
          limit: 100
        })
      // Race the two promises to see which happens faster
  
      return await Promise.race([getHomesPromise, timeoutPromise]);
  
    } catch (error) {
      console.error('Error fetching units:', error);
    }
  }

  async function addOccupant(unit, user) {

    try {
      const record = await pb.collection('units').update(unit.id, {
        occupants: [...unit.occupants, user.id]
      })
      console.log('Occupant added successfully: ', record)
    } catch (error) {
      console.error('Error adding occupant: ', error)
    }

  }

  async function removeOccupant(unit, user) {

    try {
      const record = await pb.collection('units').update(unit.id, {
        occupants: unit.occupants.filter(occupant => occupant !== user.id)
      })
      console.log('Occupant removed successfully: ', record)
    } catch (error) {
      console.error('Error removing occupant: ', error)
    }
  }

  return {
    createUnit,
    getHomeUnits,
    addOccupant,
    removeOccupant,
  };
}