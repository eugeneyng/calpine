import { toRefs, reactive, ref, watch } from "vue";
import Pocketbase from "pocketbase";

// This is intended to be a "class" for a single unit entity

export function useUnit() {
  const pb = new Pocketbase(import.meta.env.VITE_POCKETBASE_SERVER);

  const state = reactive({
    data: {},
    loading: false,
  });

  async function createItem({ name, unit, ...args }) { 
    try {
      const record = await pb.collection("inventory").create({
        name: name,
        unit: unit,
        ...args
      });
      console.log("Item created: ", record);
    } catch (error) {
      console.error("Error creating record: ", error);
    }
  }

  async function createTask({ task, ... args}) { 
    try {
      const record = await pb.collection("tasks").create({
        task: task,
        ...args
      });
      console.log("Task created: ", record);
    } catch (error) {
      console.error("Error creating record: ", error);
    }
  }

  async function deleteItem(itemId) {
    if (!itemId) return;
    state.loading = true;

    try {
      await pb.collection("inventory").delete(itemId);
      console.log("Item deleted: ", itemId);
    } catch (error) {
      console.error("Error deleting item: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function deleteTask(taskId) {
    if (!taskId) return;
    state.loading = true;

    try {
      await pb.collection("tasks").delete(taskId);
      console.log("Task deleted: ", taskId);
    } catch (error) {
      console.error("Error deleting task: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function fetchChildren() {
    if (!state.data.id) return;
    state.loading = true;

    try {
      const children = await pb.collection("units").getFullList({
        filter: `parent = "${state.data.id}"`,
        sort: "name"
      });

      return children;

    } catch (error) {
      console.error("Error fetching children: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function fetchItems() {
    if (!state.data.id) return;
    state.loading = true;

    try {
      const inventory = await pb.collection("inventory").getFullList({
        filter: `unit = "${state.data.id}"`,
        sort: "created"
      });
      return inventory;
    } catch (error) {
      console.error("Error fetching inventory: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function fetchItem(id) {
    if (!id) return;
    state.loading = true;

    try {
      const item = await pb.collection("inventory").getOne(id);
      return item;
    } catch (error) {
      console.error("Error fetching inventory item: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function fetchOccupants() {
    if (!state.data.id) return;
    state.loading = true;

    try {
      const occupants = {};

      for (const userId of state.data.occupants) {
        try {
          const occupant = await pb.collection("users").getOne(userId);
          occupants[userId] = occupant;
        } catch (error) {
          console.error(`Error fetching user ${userId}: `, error);
          occupants[userId] = null;
        }
      }
      
      return occupants;

    } catch (error) {
      console.error("Error fetching occupants: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function fetchParents() {
    if (!state.data.id) return;
    state.loading = true;
    
    const parents = {};

    async function fetchParent(id) {
      if (!id) {
        parents[id] = null;
        // console.log(("No parent"));
        return;
      }

      try {
        const parent = await pb.collection("units").getOne(id);
        parents[id] = parent;
      } catch (error) {
        console.log(`Error fetching parent: `, error);
        parent = null;
        parents[id] = parent;
      }

      // This is like, the only time I've ever used recursion
      if (parent?.parent) {
        await fetchParent(parent.parent);
      }
    }

    await fetchParent(state.data.parent);
    state.loading = false;
    return parents;
    
  }

  async function fetchTasks() {
    if (!state.data.id) return;
    state.loading = true;

    try {
      const tasks = await pb.collection("tasks").getFullList({
        filter: `unit = "${state.data.id}"`,
        sort: "created",
      });
      return tasks;
    } catch (error) {
      console.error("Error fetching tasks: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function fetchTask(id) {
    if (!id) return;
    state.loading = true;

    try {
      const task = await pb.collection("tasks").getOne(id);
      return task;
    } catch (error) {
      console.error("Error fetching task: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function fetchUnit(id) {
    if (!id) return;
    state.loading = true;

    try {
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error("Request timed out")), 10000); // 10 seconds timeout
      });
      const getUnitPromise = pb.collection("units").getOne(id);

      state.data = await Promise.race([
        getUnitPromise,
        timeoutPromise,
      ]);

    } catch (error) {
      console.error("Error fetching unit: ", error);
    } finally {
      state.loading = false;
    }
  }

  async function updateItem(item) {
    if (!item.id) return;
    state.loading = true;

    try {
      await pb.collection("inventory").update(item.id, item);
      console.log("Item updated: " + item.id);
    } catch (error) {
      console.error("Error updating item:", error);
    } finally {
      state.loading = false;
    }
  }

  async function updateTask(task) {
    if (!task.id) return;
    state.loading = true;

    try {
      await pb.collection("tasks").update(task.id, task);
      console.log("Task updated: " + task.id);
    } catch (error) {
      console.error("Error updating task:", error);
    } finally {
      state.loading = false;
    }
  }

  async function updateUnit() {
    if (!state.data.id) return;
    state.loading = true;

    try {
      await pb.collection("units").update(state.data.id, state.data);
      console.log("Unit updated: " + state.data.id);
    } catch (error) {
      console.error("Error updating unit:", error);
    } finally {
      state.loading = false;
    }
  }

  // watch(
  //   () => state.data,
  //   (newValue, oldValue) => {
  //     // This check is used to prevent the watcher from triggering the save operation when the data is first loaded.
  //     if (Object.keys(oldValue).length > 0) {
  //       // Optionally add debounce to avoid too many saves
  //       saveunit();
  //     }
  //   },
  //   { deep: true } // Deep: true ensures nested property changes are detected
  // );

  return {
    ...toRefs(state),
    createItem,
    createTask,
    deleteItem,
    deleteTask,
    fetchChildren,
    fetchItems,
    fetchItem,
    fetchOccupants,
    fetchParents,
    fetchTasks,
    fetchTask,
    fetchUnit,
    updateItem,
    updateTask,
    updateUnit,
  };
}
